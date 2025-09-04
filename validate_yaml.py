import sys, pathlib, yaml
bad = []
for p in pathlib.Path('.').rglob('metadata.yml'):
    try:
        with open(p, 'rb') as fh:
            b = fh.read()
        # убрать BOM на лету, если вдруг остался
        if b.startswith(b'\xef\xbb\xbf'):
            b = b[3:]
        yaml.safe_load(b.decode('utf-8'))
    except Exception as e:
        bad.append((str(p), str(e)))
if bad:
    print("YAML errors:")
    for path, err in bad:
        print(f" - {path}: {err}")
    sys.exit(1)
else:
    print("All metadata.yml OK")
