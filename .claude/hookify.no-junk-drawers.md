---
name: no-junk-drawers
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|[/\\])(utils|helpers|misc|common|shared|general)\.py$
action: warn
---

You're creating or editing a module with a generic name. Treat directory
structure and filenames as an interface: give every file a clear purpose.

Instead of `utils.py`, name the module after what it actually does:

- `billing/compute.py` not `billing/utils.py`
- `auth/tokens.py` not `auth/helpers.py`
- `parsing/csv_reader.py` not `common/misc.py`

Name shared code after its responsibility and place it with related code.
Prefer a shared package that centralizes invariants over custom helpers
scattered across domains. If only one module uses the functions, keep them in
that module.
