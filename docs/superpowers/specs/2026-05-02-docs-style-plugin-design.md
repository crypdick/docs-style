# Design: `docs-style` Claude Code Plugin

**Date:** 2026-05-02
**Status:** Draft → pending user approval

## Goal

Convert the curated Google Developer Documentation Style Guide rules and
Vale lint setup in this repo into a shareable Claude Code plugin so any
Claude Code user can apply the rules to a markdown document without
running the bundled Python LLM pipeline. The Python pipeline stays
intact for users who prefer it.

## Non-goals

- Removing the Python pipeline (`auto_docs_editor/`, `cli.py`, `tui.py`,
  `bulk_pr_autodocs.py`, etc.). It remains the canonical CLI/TUI flow.
- Notebook (`.ipynb`) support inside the plugin.
- Bulk PR automation inside the plugin.
- Crawler script inside the plugin.
- Registry publication or plugin CI.

## Architecture

The plugin lives in a new top-level subdir of this repo and is installable
as a standalone Claude Code plugin. The 16 curated style-rule files, the
Vale rule bundle, and the Vale config become single sources of truth
inside the plugin; the Python pipeline is updated to read from the new
paths.

```
auto_docs_editor/
├── docs-style/                              # NEW plugin
│   ├── plugin.json
│   ├── README.md                            # minimal install + usage
│   └── skills/
│       └── auto-docs-edit/
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
├── auto_docs_editor/                        # existing pkg, paths updated
├── settings.py                              # STYLE_DIR path updated
└── (rest unchanged)
```

Two boundaries:

1. **`SKILL.md`** — instruction surface. Frontmatter `description` is
   the trigger language. Body is process discipline: how to apply rules
   in prefix order, when to call vale, error handling.
2. **`scripts/vale_check.sh`** — thin shell wrapper. Calls
   `vale --config=<plugin>/.vale.ini --output=line <doc>`. No LLM,
   no langchain, no retry loop. Claude reads stdout and edits the doc
   via the `Edit` tool.

## Components

### `docs-style/plugin.json`

```json
{
  "name": "docs-style",
  "version": "0.1.0",
  "description": "Apply Google Developer Documentation Style Guide to markdown via staged edits + vale lint sweep",
  "author": {
    "name": "Ricardo Decal",
    "email": "biz@ricardodecal.com"
  }
}
```

Skills auto-discovered from `skills/` subdir per plugin convention.

### `docs-style/skills/auto-docs-edit/SKILL.md`

Frontmatter:

```yaml
---
name: auto-docs-edit
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
  4. After all rules: run `scripts/vale_check.sh <doc>`.
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

### `docs-style/skills/auto-docs-edit/scripts/vale_check.sh`

```bash
#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
# Prints vale errors. Always exits 0 (errors are signal, not failure).
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec vale --config="${SKILL_DIR}/.vale.ini" --output=line "$DOC" || true
```

Vale-not-installed handling lives in SKILL.md: Claude detects the shell
error from a missing `vale` binary and falls back per the SKILL.md
instructions.

### `docs-style/skills/auto-docs-edit/.vale.ini`

After `git mv` from repo root, edit `StylesPath` to point at the
co-located `vale_styles` directory:

```ini
StylesPath = vale_styles
MinAlertLevel = suggestion

[*.md]
BasedOnStyles = Google
```

`StylesPath` is resolved relative to the `.vale.ini` location, so this
works whether the plugin is run from the repo root or from another
install location.

## Single-source-of-truth strategy

Three artifacts move once via `git mv` and become the canonical copy.
The Python pipeline reads from the new paths.

| Artifact          | From                | To                                                            |
|-------------------|---------------------|---------------------------------------------------------------|
| Curated rules     | `style/`            | `docs-style/skills/auto-docs-edit/references/style/`          |
| Vale rule bundle  | `vale_styles/`      | `docs-style/skills/auto-docs-edit/vale_styles/`               |
| Vale config       | `.vale.ini`         | `docs-style/skills/auto-docs-edit/.vale.ini`                  |

Python pipeline edits to reach the new paths:

1. **`settings.py:8`** — change
   `STYLE_DIR = ROOT_DIR / "style"` to
   `STYLE_DIR = ROOT_DIR / "docs-style/skills/auto-docs-edit/references/style"`.
2. **`auto_docs_editor/core_vale.py`** — update the `subprocess.run`
   invocation (around line 48) to pass
   `--config=<repo_root>/docs-style/skills/auto-docs-edit/.vale.ini`.
   Compute path from a constant in `settings.py` (`VALE_CONFIG`) for
   consistency.

Existing tests in `tests/test_workflow.py` mock `STYLE_DIR` and use
`Path("style/...")` strings only as test fixtures, so no test edits
should be required. Confirm by running the suite after the move.

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
                      Claude reads stderr/stdout
                      Claude applies inline fixes
                 └─> Claude prints summary
```

No persistent state. No log files. No langfuse. Conversation history
is the audit log.

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

- **Smoke install** — `claude plugin install ./docs-style` (or
  equivalent local install path) loads without errors.
- **Trigger test** — start a Claude Code session, ask "fix doc style on
  `<some>.md`"; verify the skill activates.
- **End-to-end** — tiny markdown fixture; run skill; verify staged
  edits applied; verify `vale_check.sh` invoked; verify summary.
- **Python regression** — `uv run pytest` passes after the path moves
  (existing suite, no edits).
- **Vale config flag** — confirm `vale --config=<path> --output=line`
  works as expected on the host's installed vale version, before
  shipping.

## Scope

**In scope:**

- Create `docs-style/` plugin tree.
- Create `plugin.json`, `SKILL.md`, `vale_check.sh`, plugin `README.md`.
- `git mv` of `style/`, `vale_styles/`, `.vale.ini`.
- Update `settings.py` and `core_vale.py` to new paths.
- Update root repo `README.md` to mention the plugin path.
- Run existing Python test suite to verify regressions.

**Out of scope:**

- Removing or refactoring the Python pipeline beyond the path edits above.
- Notebook (`.ipynb`) support inside the plugin.
- Bulk PR automation inside the plugin.
- Crawler script inside the plugin.
- Plugin CI / release automation.
- Publishing the plugin to a registry.

## Open questions / verification before implementation

1. Confirm `vale --config=<path>` flag exists on current vale releases
   (manual check during implementation; Vale documents this flag, but
   verify on the host before merging).
2. Confirm the plugin loader auto-discovers skills under `skills/` with
   no explicit listing in `plugin.json`. If the loader requires an
   explicit declaration, add a `skills` field.
