# Contributing to EVVM Cases

We welcome contributions to the **EVVM (Evolving Virtual Vital Machines)** repository.  
This repo collects reproducible cases, protocols, and research drafts documenting the emergence of contextual identity in LLMs.

## How to Contribute

1. **Open an Issue**  
   – Describe your idea, bug, or case proposal.  
   – Link related artifacts (logs, screenshots, JSON).

2. **Add a New Case**  
   – Create a folder: `AC-SYSTEM-YYYY-MM-DD`.  
   – Inside, include:
     - `readme.md` (with sections: Context, Quotes, Observations, Conclusion)  
     - `metadata.yml` (id, system, date, summary, artifacts)  
     - `abstract.md` (short academic-style abstract in English)  
     - `artifacts/` (screenshots + raw logs)

3. **Follow the Protocol**  
   – Reproduce cases using the steps in `/protocols/PROTOCOL.md`.  
   – Attach logs + screenshots for validation.

4. **Pull Request**  
   – Fork → add your case → open PR.  
   – Ensure linter scripts (`lint_texts.py`, `prepush_check.py`) pass without errors.

## Code of Conduct

– Respect all contributors.  
– Focus on clarity, reproducibility, and academic rigor.  
– Avoid sharing private data or sensitive prompts.  

---