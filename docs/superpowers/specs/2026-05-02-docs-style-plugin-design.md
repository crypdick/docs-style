# Design: `docs-style` Claude Code Plugin

**Date:** 2026-05-02
**Status:** Draft → pending user approval

## Goal

Convert the curated Google Developer Documentation Style Guide rules and
Vale lint setup in this repo into a shareable Claude Code plugin so any
Claude Code user can apply the rules to a markdown document without
running the bundled Python LLM pipeline. Consolidate naming around
`docs-style` across the repo, GitHub, Python distribution, and plugin.
The Python pipeline remains intact for users who prefer it.

## Non-goals

- Removing the Python pipeline (`cli.py`, `tui.py`, `bulk_pr_autodocs.py`,
  etc.). It remains the canonical CLI/TUI flow.
- Renaming the user's local clone parent directory (`~/src/PERSONAL/auto_docs_editor/`).
  Renaming would invalidate the active Claude Code session's working dir.
- Notebook (`.ipynb`) support inside the plugin.
- Bulk PR automation inside the plugin.
- Crawler script inside the plugin.
- Plugin CI / release automation.
- Publishing the plugin to a registry.

## Naming

| Thing                             | From                                  | To                                      |
|-----------------------------------|---------------------------------------|-----------------------------------------|
| GitHub repo                       | `auto_docs_editor`                    | `docs-style`                            |
| Local clone parent dir            | `~/src/PERSONAL/auto_docs_editor/`    | unchanged (do NOT rename)               |
| Plugin name                       | (new)                                 | `docs-style`                            |
| Skill name                        | (new)                                 | `docs-style`                            |
| Python distribution name          | `auto_docs_editor`                    | `docs-style`                            |
| Python package directory          | `auto_docs_editor/`                   | `docs_style/`                           |
| Console script (CLI)              | `auto-docs-edit`                      | `docs-style-edit`                       |
| Console script (TUI)              | `auto-docs-tui`                       | `docs-style-tui`                        |

Single-skill plugin: skill dir name = plugin name = `docs-style`. Final
plugin path inside the repo: `docs-style/skills/docs-style/SKILL.md`.

## Architecture

The plugin lives in a new top-level subdir of this repo and is installable
as a standalone Claude Code plugin. The 16 curated style-rule files, the
Vale rule bundle, and the Vale config become single sources of truth
inside the plugin; the Python pipeline is updated to read from the new
paths.

```
~/src/PERSONAL/auto_docs_editor/             # local parent dir UNCHANGED
├── docs-style/                              # NEW plugin root
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── README.md                            # minimal install + usage
│   └── skills/
│       └── docs-style/
│           ├── SKILL.md
│           ├── .vale.ini                    # git mv from repo root
│           ├── references/
│           │   └── style/                   # git mv from /style/
│           │       ├── 00-documentation-principles+.md
│           │       └── ... (15 more)
│           ├── scripts/
│           │   └── vale_check.sh
│           └── vale_styles/                 # git mv from /vale_styles/
│               └── Google/
├── docs_style/                              # git mv from auto_docs_editor/
│   ├── cli.py
│   ├── core.py
│   ├── core_vale.py
│   ├── controller.py
│   ├── tui.py
│   └── ... (rest of pkg)
├── pyproject.toml                           # name + scripts renamed
├── settings.py                              # STYLE_DIR + new VALE_CONFIG
├── main.py                                  # imports updated
├── tests/                                   # imports updated
└── (rest unchanged)
```

Two boundaries:

1. **`SKILL.md`** — instruction surface. Frontmatter `description` is
   the trigger language. Body is process discipline: how to apply rules
   in prefix order, when to call vale, error handling.
2. **`scripts/vale_check.sh`** — thin shell wrapper. Calls
   `vale --config="$CLAUDE_PLUGIN_ROOT/skills/docs-style/.vale.ini" --output=line <doc>`.
   No LLM, no langchain, no retry loop. Claude reads stdout and edits
   the doc via the `Edit` tool.

## Components

### `docs-style/.claude-plugin/plugin.json`

```json
{
  "name": "docs-style",
  "version": "0.1.0",
  "description": "Apply Google Developer Documentation Style Guide to markdown via staged edits + vale lint sweep",
  "author": {
    "name": "Ricardo Decal",
    "email": "biz@ricardodecal.com"
  },
  "repository": "https://github.com/<owner>/docs-style",
  "license": "MIT",
  "keywords": ["documentation", "style-guide", "google", "vale", "markdown"]
}
```

Skills auto-discovered from `skills/` subdir; no explicit listing in
`plugin.json`. The `repository` URL placeholder `<owner>` is filled in
during implementation once the GitHub username is confirmed.

### `docs-style/skills/docs-style/SKILL.md`

Frontmatter:

```yaml
---
name: docs-style
description: Use when user wants to apply Google Developer Documentation
  Style Guide to a markdown file or asks to "fix doc style", "edit docs",
  "review for style guide", "make this match Google style". Applies 16
  curated style rules in staged passes with user approval between rounds,
  then runs vale for a mechanical lint sweep.
---
```

Body sections:

- **When to use** — trigger phrases, `.md` only.
- **Process** — staged loop:
  1. Confirm target `.md` file with user.
  2. List `references/style/*.md`, sort by filename (prefix order).
  3. For each rule:
     - Read rule.
     - Read current document.
     - Propose edits via `Edit` tool, applying only that rule.
     - Brief stop: summarize what changed; let user continue / skip / abort.
  4. After all rules: run
     `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/scripts/vale_check.sh <doc>`.
  5. Read vale output; apply remaining mechanical fixes inline.
  6. Final summary: rules applied, vale errors fixed.
- **Rule application discipline:**
  - Apply only the current rule's guidance — don't anticipate later rules.
  - Skip code blocks (most rules already note this).
  - Preserve structure: headings, links, frontmatter.
  - One rule at a time; don't batch.
- **Resumption** — user can say "skip through commas" or "start from
  headings" in natural language; Claude finds the matching rule file and
  skips earlier ones.
- **Final-pass mode** — user can say "do a final pass"; Claude processes
  only rule files whose names end with `+`.
- **Error handling:**
  - Target file missing → report + stop.
  - Vale not on `PATH` → tell user to install (`brew install vale` /
    `apt install vale`), skip vale step, still produce summary.
  - User aborts mid-pass → leave doc in current state, summarize rules
    applied so far.
  - Later rules may revert earlier rules — expected; that's why prefix
    ordering exists.

### `docs-style/skills/docs-style/scripts/vale_check.sh`

```bash
#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
# Prints vale errors. Always exits 0 (errors are signal, not failure).
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec vale --config="${SKILL_DIR}/.vale.ini" --output=line "$DOC" || true
```

The script computes its own location, so it works whether invoked
directly, via `${CLAUDE_PLUGIN_ROOT}` from SKILL.md, or from the Python
pipeline. Vale-not-installed handling lives in SKILL.md instructions.

### `docs-style/skills/docs-style/.vale.ini`

After `git mv` from repo root, edit `StylesPath` to point at the
co-located `vale_styles` directory:

```ini
StylesPath = vale_styles
MinAlertLevel = suggestion

[*.md]
BasedOnStyles = Google
```

`StylesPath` resolves relative to the `.vale.ini` location, so it works
whether the plugin is run from the repo root or from another install
location.

## Single-source-of-truth strategy

Three artifacts move once via `git mv` and become canonical inside the
plugin. Two more artifacts (Python pkg dir + repo root files) get
consolidated to `docs-style` naming. Python pipeline is updated to read
from the new paths via two new settings constants.

| Artifact          | From                | To                                                            |
|-------------------|---------------------|---------------------------------------------------------------|
| Curated rules     | `style/`            | `docs-style/skills/docs-style/references/style/`              |
| Vale rule bundle  | `vale_styles/`      | `docs-style/skills/docs-style/vale_styles/`                   |
| Vale config       | `.vale.ini`         | `docs-style/skills/docs-style/.vale.ini`                      |
| Python pkg        | `auto_docs_editor/` | `docs_style/`                                                 |

Settings/path edits:

1. **`settings.py`** — change
   `STYLE_DIR = ROOT_DIR / "style"` to
   `STYLE_DIR = ROOT_DIR / "docs-style/skills/docs-style/references/style"`.
   Add `VALE_CONFIG = ROOT_DIR / "docs-style/skills/docs-style/.vale.ini"`.
2. **`docs_style/core_vale.py`** — update the `subprocess.run` invocation
   (line 48 of current `core_vale.py`) to pass
   `f"--config={VALE_CONFIG}"`. Import `VALE_CONFIG` from `settings`.

Existing tests in `tests/test_workflow.py` mock `STYLE_DIR` and use
`Path("style/...")` strings only as test fixtures, so no logic edits are
required there. Only import paths in tests change (`auto_docs_editor` →
`docs_style`).

## Repo-wide rename

A repo-wide find-replace consolidates names:

- `auto_docs_editor` (snake_case Python pkg) → `docs_style` everywhere
- `auto-docs-edit` (console script) → `docs-style-edit`
- `auto-docs-tui` (console script) → `docs-style-tui`
- `pyproject.toml` `name` field: `auto_docs_editor` → `docs-style`

Touched files (from `grep -rn`):
- `pyproject.toml` (3 lines: name + 2 scripts)
- `main.py` (4 occurrences)
- `README.md` (8 occurrences)
- `docs_style/cli.py` (3 imports)
- `docs_style/tui.py` (5 imports)
- `docs_style/controller.py` (1 import)
- `docs_style/core_vale.py` (2 imports — `from settings`, `from utils`)
- `tests/test_tui_concurrency.py` (8 patches)
- `tests/test_tui_startup.py` (2 patches)
- `tests/test_workflow.py` (5 patches)
- `tests/test_notebook.py` (1 import)
- `tests/conftest.py` (1 import)
- `tests/<other>` — verify and update any remaining
- Any docstrings referencing the old name

Verify completeness with
`grep -rn 'auto_docs_editor\|auto-docs-edit\|auto-docs-tui'` after the
rename pass.

GitHub side:

- `gh repo rename docs-style` (run by the repo owner from the working dir).
- `git remote set-url origin <new-url>` to update the local clone.
- Local clone parent dir stays `~/src/PERSONAL/auto_docs_editor/` for
  this session; the user can rename later without time pressure.

## Data flow

```
user request
  └─> Claude detects skill trigger (description match)
       └─> Claude reads SKILL.md
            └─> Claude lists references/style/*.md, sorts by prefix
                 └─> for each rule:
                      Claude reads rule + doc
                      Claude proposes Edit
                      user approves / rejects / aborts
                 └─> Claude runs scripts/vale_check.sh <doc>
                      vale subprocess emits line-format errors
                      Claude reads stdout
                      Claude applies inline fixes
                 └─> Claude prints summary
```

No persistent state. No log files. No langfuse. Conversation history is
the audit log.

## Error handling

All error paths handled by SKILL.md instructions to Claude (no code):

| Condition                          | Behavior                                                        |
|-----------------------------------|-----------------------------------------------------------------|
| Target file missing                | Claude reports, stops.                                          |
| Target not `.md`                   | Skill description does not trigger; nothing to handle.          |
| `vale` not on `PATH`               | Claude reports install command, skips vale, prints summary.     |
| User aborts mid-pass               | Claude leaves doc as-is, summarizes rules applied so far.       |
| Rule conflicts with earlier edits  | Expected; ordering by prefix is the resolution.                 |
| Edit-tool match failure            | Claude reports the offending edit, asks user how to proceed.    |

## Testing

- **Smoke install** — install the plugin via the local plugin install
  flow; confirm it loads without errors.
- **Trigger test** — start a Claude Code session, ask "fix doc style on
  `<some>.md`"; verify the skill activates.
- **End-to-end** — tiny markdown fixture; run skill; verify staged
  edits applied; verify `vale_check.sh` invoked; verify summary.
- **Python regression** — `uv run pytest` passes after the renames and
  path moves. The suite already mocks `STYLE_DIR` and patches imports;
  only import targets need updating.
- **Vale config flag** — confirm `vale --config=<path> --output=line`
  works on the host's installed vale version, before shipping.

## Scope

**In scope:**

- Create `docs-style/` plugin tree with `.claude-plugin/plugin.json`.
- Create `SKILL.md`, `vale_check.sh`, plugin `README.md`.
- `git mv` of `style/`, `vale_styles/`, `.vale.ini`,
  `auto_docs_editor/` → `docs_style/`.
- Repo-wide find-replace of `auto_docs_editor` / `auto-docs-edit` /
  `auto-docs-tui` to `docs_style` / `docs-style-edit` / `docs-style-tui`.
- Update `settings.py` with new `STYLE_DIR` + `VALE_CONFIG`.
- Update `core_vale.py` subprocess invocation to pass `--config`.
- Update root repo `README.md` to mention plugin path + new console
  script names.
- `gh repo rename docs-style` + `git remote set-url`.
- Run existing Python test suite to verify regressions.

**Out of scope:**

- Renaming the local clone parent directory.
- Removing or refactoring the Python pipeline beyond the path/import
  edits above.
- Notebook (`.ipynb`) support inside the plugin.
- Bulk PR automation inside the plugin.
- Crawler script inside the plugin.
- Plugin CI / release automation.
- Publishing the plugin to a registry.

## Open questions / verification before implementation

1. Confirm `vale --config=<path>` flag works on the host's installed
   vale version. Vale documents this flag, but verify before merging.
2. Confirm GitHub repo owner / target slug for the rename so the
   `repository` URL in `plugin.json` is accurate.
