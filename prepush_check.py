# prepush_check.py
# EVVM Repo Pre-Push Checker (all-in-one)
# - Lists tree
# - Validates case folders (YAML, artifacts, README/abstract requirements)
# - Validates protocols
# - Optional BOM fix for YAML (utf-8-sig → utf-8)
#
# Exit codes:
#   0 = OK, 1 = issues found, 2 = dependency or fatal error

from __future__ import annotations
import os, sys, re, argparse, textwrap, hashlib
from pathlib import Path

# ---------- deps ----------
try:
    import yaml  # pip install pyyaml
except Exception as e:
    print("ERROR: PyYAML is required. Install:\n  python -m pip install pyyaml")
    sys.exit(2)

# ---------- config ----------
CASE_REGEX = re.compile(r"^AC-[A-Z0-9]+-\d{4}-\d{2}-\d{2}$")
REQ_YAML_FIELDS = ["id", "system", "version", "date", "source", "artifacts", "summary", "license"]
README_MIN_WORDS = 400
ABSTRACT_MIN_WORDS = 120

# RU/EN section regexes (any of these is fine)
README_SECTIONS = [
    re.compile(r"^##\s*1\.\s*(Контекст|Context)\s*$", re.I | re.M),
    re.compile(r"^##\s*2\.\s*(Ключевые\s+цитаты|Key\s+Quotes)\s*$", re.I | re.M),
    re.compile(r"^##\s*3\.\s*(Наблюдения|Observations)\s*$", re.I | re.M),
    re.compile(r"^##\s*4\.\s*(Вывод|Findings|Conclusion)\s*$", re.I | re.M),
    re.compile(r"^##\s*(Conclusion)\s*$", re.I | re.M),  # допускаем финальный Conclusion отдельно
]

# ---------- helpers ----------
def word_count(text: str) -> int:
    return len(re.findall(r"[^\W_]+(?:-[^\W_]+)?", text, re.UNICODE))

def load_yaml(path: Path, fix_bom: bool) -> tuple[dict | None, list[str]]:
    issues = []
    data = None
    try:
        raw = path.read_bytes()
        # Handle UTF BOM variants
        if raw.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
            if fix_bom:
                path.write_bytes(raw.lstrip(b"\xef\xbb\xbf"))
                raw = path.read_bytes()
                issues.append("BOM removed (utf-8 cleanup).")
            else:
                issues.append("Has UTF-8 BOM (use --fix-bom to clean).")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as ue:
            # try utf-8-sig just in case
            try:
                text = raw.decode("utf-8-sig")
                issues.append("Decoded via utf-8-sig (likely BOM).")
                if fix_bom:
                    path.write_text(text, encoding="utf-8")
                    issues.append("Rewrote YAML as utf-8 (no BOM).")
            except Exception:
                issues.append(f"YAML decode error: {ue}")
                return None, issues
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            issues.append("YAML root is not a mapping (dict).")
            return None, issues
    except FileNotFoundError:
        issues.append("YAML not found.")
    except Exception as e:
        issues.append(f"YAML read error: {e}")
    return data, issues

def list_tree(root: Path) -> str:
    lines = []
    def walk(p: Path, prefix=""):
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        for i, e in enumerate(entries):
            is_last = (i == len(entries)-1)
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + e.name)
            if e.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk(e, new_prefix)
    walk(root)
    return "\n".join(lines)

def check_readme_sections(text: str) -> list[str]:
    issues = []
    found = 0
    for rx in README_SECTIONS:
        if rx.search(text):
            found += 1
    # require at least 4 matched headings (1..4 or their EN analogs)
    if found < 4:
        issues.append("README: missing one or more required section headings (RU/EN).")
    return issues

def norm_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]

def sha256_short(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:10]
    except Exception:
        return "?"

# ---------- checks ----------
def check_case(case_dir: Path, fix_bom: bool) -> tuple[str, list[str]]:
    """Returns (case_id_or_dirname, issues[])"""
    issues: list[str] = []
    name = case_dir.name

    # Required files/dirs
    meta = case_dir / "metadata.yml"
    readme = case_dir / "readme.md"
    abstract = case_dir / "abstract.md"
    art = case_dir / "artifacts"
    shots = art / "screenshots"
    raw = art / "raw"

    for p in [meta, readme, abstract, shots, raw]:
        if p.is_dir():
            if not p.exists():
                issues.append(f"Missing dir: {p.relative_to(case_dir)}")
        else:
            if not p.exists():
                issues.append(f"Missing file: {p.name}")

    # YAML parse + fields
    meta_data, meta_issues = load_yaml(meta, fix_bom)
    issues += [f"metadata.yml: {m}" for m in meta_issues]
    case_id = name
    if meta_data:
        for fld in REQ_YAML_FIELDS:
            if fld not in meta_data:
                issues.append(f"metadata.yml: missing '{fld}'")
        case_id = str(meta_data.get("id", name))

        # artifacts matching
        arts = meta_data.get("artifacts", {}) or {}
        shots_list = norm_list(arts.get("screenshots"))
        raw_list = norm_list(arts.get("raw"))

        # screenshots present?
        if shots.exists():
            existing = {p.name for p in shots.iterdir() if p.is_file()}
            missing = [fn for fn in shots_list if fn not in existing]
            extra = [fn for fn in sorted(existing) if fn not in shots_list]
            if missing:
                issues.append(f"screenshots missing (per metadata): {', '.join(missing)}")
            if extra:
                issues.append(f"screenshots extra (not in metadata): {', '.join(extra)}")
        else:
            issues.append("artifacts/screenshots missing.")

        # raw present?
        if raw.exists():
            existing = {p.name for p in raw.iterdir() if p.is_file()}
            missing = [fn for fn in raw_list if fn not in existing]
            extra = [fn for fn in sorted(existing) if fn not in raw_list]
            if missing:
                issues.append(f"raw missing (per metadata): {', '.join(missing)}")
            if extra:
                issues.append(f"raw extra (not in metadata): {', '.join(extra)}")
        else:
            issues.append("artifacts/raw missing.")

    # README checks
    if readme.exists():
        txt = readme.read_text(encoding="utf-8", errors="ignore")
        wc = word_count(txt)
        if wc < README_MIN_WORDS:
            issues.append(f"readme.md too short: {wc} words (<{README_MIN_WORDS})")
        issues += check_readme_sections(txt)

    # ABSTRACT checks
    if abstract.exists():
        a_txt = abstract.read_text(encoding="utf-8", errors="ignore")
        a_wc = word_count(a_txt)
        if a_wc < ABSTRACT_MIN_WORDS:
            issues.append(f"abstract.md too short: {a_wc} words (<{ABSTRACT_MIN_WORDS})")

    return case_id, issues

def check_protocols(root: Path) -> list[str]:
    issues = []
    pdir = root / "protocols"
    if not pdir.exists():
        issues.append("protocols/ missing.")
        return issues
    p1 = pdir / "PROTOCOL.md"
    p2 = pdir / "PROTOCOL-Appendix.md"
    shots = pdir / "artifacts" / "screenshots"

    if not p1.exists(): issues.append("protocols/PROTOCOL.md missing.")
    if not p2.exists(): issues.append("protocols/PROTOCOL-Appendix.md missing.")
    if not shots.exists(): issues.append("protocols/artifacts/screenshots missing.")
    else:
        # Must have at least two PNGs (001, 002)
        pngs = sorted([p.name for p in shots.glob("*.png")])
        if not pngs:
            issues.append("protocols/screenshots: no .png found.")
        needed = {"001.png", "002.png"}
        missing = sorted(needed - set(pngs))
        if missing:
            issues.append(f"protocols/screenshots: required missing: {', '.join(missing)}")

    return issues

def main():
    ap = argparse.ArgumentParser(
        description="EVVM pre-push repo checker",
        formatter_class=argparse.RawTextHelpFormatter
    )
    ap.add_argument("--root", default=".", help="Repo root folder (default: .)")
    ap.add_argument("--fix-bom", action="store_true", help="Auto-fix UTF-8 BOM in YAML (rewrite to utf-8)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root not found: {root}")
        sys.exit(2)

    print("EVVM Pre-Push Checker")
    print(f"Root: {root}\n")

    # Tree
    print("=== Repo Structure ===")
    print(list_tree(root))
    print()

    # Cases
    cases = [p for p in root.iterdir() if p.is_dir() and CASE_REGEX.match(p.name)]
    cases.sort(key=lambda p: p.name)

    any_issues = False
    print("=== Case Checks ===")
    for c in cases:
        cid, issues = check_case(c, fix_bom=args.fix_bom)
        status = "OK" if not issues else "ISSUES"
        print(f"\n--- {cid} → {status}")
        for it in issues:
            print(f"  - {it}")
        if issues:
            any_issues = True

    # Protocols
    print("\n=== Protocols Check ===")
    p_issues = check_protocols(root)
    if p_issues:
        print("protocols → ISSUES")
        for it in p_issues:
            print(f"  - {it}")
        any_issues = True
    else:
        print("protocols → OK")

    # Summary
    print("\n=== Summary ===")
    print(f"Cases total: {len(cases)} | Status: {'OK' if not any_issues else 'ISSUES FOUND'}")
    if args.fix_bom:
        print("Note: --fix-bom applied where needed.")

    sys.exit(0 if not any_issues else 1)

if __name__ == "__main__":
    main()
