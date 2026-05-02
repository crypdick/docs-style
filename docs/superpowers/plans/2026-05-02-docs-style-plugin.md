# `docs-style` Claude Code Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert this repo's curated Google Style Guide rules + Vale lint setup into a shareable Claude Code plugin (`docs-style`), and consolidate naming around `docs-style` across GitHub, Python distribution, and console scripts. Python pipeline keeps working from new paths.

**Architecture:** Single-skill plugin under `docs-style/` subdir of the repo. `.claude-plugin/plugin.json` manifest + `skills/docs-style/SKILL.md` instructs Claude to apply 16 staged style rules and run a vale wrapper script for a final mechanical sweep. Style assets (`style/`, `vale_styles/`, `.vale.ini`) live inside the plugin tree as the single source of truth. Python pipeline reads from those paths via two `settings.py` constants. Repo-wide find-replace renames the Python package, distribution, and console scripts.

**Tech Stack:** Bash (vale wrapper), Markdown (SKILL.md, rule files), JSON (plugin manifest), Python 3.12+ (existing pipeline reads from new paths), Vale CLI, `git mv` for history-preserving moves.

**Spec:** `docs/superpowers/specs/2026-05-02-docs-style-plugin-design.md`

---

## File Structure

**New files (additive):**

| Path                                                       | Responsibility                                                        |
|------------------------------------------------------------|-----------------------------------------------------------------------|
| `docs-style/.claude-plugin/plugin.json`                    | Plugin manifest. Name, version, author, repo URL, keywords.           |
| `docs-style/README.md`                                     | Minimal plugin install + usage instructions.                          |
| `docs-style/skills/docs-style/SKILL.md`                    | Skill description + staged-pass workflow + vale invocation + errors.  |
| `docs-style/skills/docs-style/scripts/vale_check.sh`       | Bash wrapper around `vale --config=… --output=line <doc>`.            |

**Moved via `git mv` (history preserved):**

| From                  | To                                                            |
|-----------------------|---------------------------------------------------------------|
| `style/`              | `docs-style/skills/docs-style/references/style/`              |
| `vale_styles/`        | `docs-style/skills/docs-style/vale_styles/`                   |
| `.vale.ini`           | `docs-style/skills/docs-style/.vale.ini`                      |
| `auto_docs_editor/`   | `docs_style/`                                                 |

**Modified files:**

| Path                            | Why                                                                          |
|---------------------------------|------------------------------------------------------------------------------|
| `settings.py`                   | Update `STYLE_DIR`; add `VALE_CONFIG`.                                       |
| `docs_style/core_vale.py`       | Add `--config={VALE_CONFIG}` to `subprocess.run` invocation.                 |
| `pyproject.toml`                | `name = "docs-style"`; rename two `[project.scripts]` entries.               |
| `main.py`                       | Update import paths + printed usage strings.                                 |
| `README.md` (root)              | Update console script names + plugin path mention.                           |
| `tests/conftest.py`             | Update import.                                                               |
| `tests/test_*.py` (multiple)    | Update `auto_docs_editor` imports + `patch()` strings → `docs_style`.        |
| `docs-style/skills/docs-style/.vale.ini` | Edit `StylesPath` after move.                                       |

**External (one-shot, not a file edit):**

- `gh repo rename docs-style`
- `git remote set-url origin <new url>`

---

## Task 1: Pre-flight verification

**Goal:** Confirm prerequisites before touching files. No commits.

**Files:** none.

- [ ] **Step 1: Verify vale `--config` flag exists**

```bash
vale --help 2>&1 | grep -E "\-\-config|config-file" || echo "MISSING"
```

Expected: line containing `--config` (or similar). If output shows `MISSING`, fall back to using `VALE_CONFIG_PATH` env var inside `vale_check.sh` and `core_vale.py` instead of `--config=`. Re-read Vale docs in that case before proceeding.

If `vale` is not installed locally, skip this check and note the verification must run on a machine with vale installed before merging.

- [ ] **Step 2: Capture current GitHub repo owner**

```bash
git -C /home/ricardo/src/PERSONAL/auto_docs_editor remote -v | head -1
```

Expected: `origin  git@github.com:<owner>/auto_docs_editor.git (fetch)` or `https://github.com/<owner>/auto_docs_editor.git`.

Record `<owner>` for use in `plugin.json` `repository` field in Task 4.

- [ ] **Step 3: Confirm test suite is green before any changes**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor && uv run pytest -x
```

Expected: all tests pass. If any fail at baseline, stop and fix or document the failure before proceeding — otherwise downstream regressions can't be distinguished.

- [ ] **Step 4: Confirm baseline grep counts (rename targets)**

```bash
grep -rn 'auto_docs_editor\|auto-docs-edit\|auto-docs-tui' \
  --include="*.py" --include="*.toml" --include="*.md" \
  /home/ricardo/src/PERSONAL/auto_docs_editor/ 2>/dev/null \
  | grep -v __pycache__ | grep -v archive | grep -v "docs/superpowers" \
  | wc -l
```

Expected: `111` (current count). Used as a sanity check after Task 8 — count should drop to `0`.

---

## Task 2: Migrate style assets and update Python paths atomically

**Goal:** Move `style/`, `vale_styles/`, `.vale.ini` into the plugin tree, then immediately update `settings.py` and `core_vale.py` so the Python pipeline still works. One commit, tests must pass at end.

**Files:**
- Create dirs: `docs-style/skills/docs-style/{references,scripts}/`
- Move: `style/`, `vale_styles/`, `.vale.ini`
- Modify: `settings.py`, `docs-style/skills/docs-style/.vale.ini`, `auto_docs_editor/core_vale.py`

- [ ] **Step 1: Create plugin skeleton dirs**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
mkdir -p docs-style/.claude-plugin
mkdir -p docs-style/skills/docs-style/references
mkdir -p docs-style/skills/docs-style/scripts
```

Expected: 4 new empty dirs. `git status` shows them as untracked (empty dirs aren't tracked yet — populated by `git mv` next).

- [ ] **Step 2: Move curated style rules**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git mv style docs-style/skills/docs-style/references/style
```

Expected: `git status -s` shows 16 `R` (renamed) entries from `style/*.md` → `docs-style/skills/docs-style/references/style/*.md`.

Verify count:
```bash
ls docs-style/skills/docs-style/references/style/ | wc -l
```
Expected: `16`.

- [ ] **Step 3: Move vale rule bundle**

```bash
git mv vale_styles docs-style/skills/docs-style/vale_styles
```

Expected: `git status -s` shows further `R` entries for everything under `vale_styles/Google/`.

- [ ] **Step 4: Move vale config**

```bash
git mv .vale.ini docs-style/skills/docs-style/.vale.ini
```

Expected: one more `R` entry.

- [ ] **Step 5: Confirm `.vale.ini` `StylesPath` already correct**

```bash
cat docs-style/skills/docs-style/.vale.ini
```

Expected output:
```
StylesPath = vale_styles
MinAlertLevel = suggestion

# Packages = Google

[*.md]
BasedOnStyles = Google
```

`StylesPath = vale_styles` resolves relative to the `.vale.ini` location, so it now points at the co-located `docs-style/skills/docs-style/vale_styles/` dir. No edit needed unless the existing path differs from `vale_styles`.

- [ ] **Step 6: Update `settings.py`**

Edit `/home/ricardo/src/PERSONAL/auto_docs_editor/settings.py`. Change line 8:

```python
STYLE_DIR = ROOT_DIR / "style"
```

to:

```python
STYLE_DIR = ROOT_DIR / "docs-style" / "skills" / "docs-style" / "references" / "style"
VALE_CONFIG = ROOT_DIR / "docs-style" / "skills" / "docs-style" / ".vale.ini"
```

`VALE_CONFIG` is added immediately after `STYLE_DIR` so both path constants live together.

- [ ] **Step 7: Update `core_vale.py` subprocess invocation**

Edit `/home/ricardo/src/PERSONAL/auto_docs_editor/auto_docs_editor/core_vale.py`. Add the import (top of file, with other settings imports):

```python
from settings import MODEL_NAME, VALE_CONFIG
```

Replacing the existing `from settings import MODEL_NAME` line.

Then change the `subprocess.run` call (around line 47–52):

```python
            result = subprocess.run(
                ["vale", "--output=line", str(document_path)],
                capture_output=True,
                text=True,
                check=False,
            )
```

to:

```python
            result = subprocess.run(
                ["vale", f"--config={VALE_CONFIG}", "--output=line", str(document_path)],
                capture_output=True,
                text=True,
                check=False,
            )
```

- [ ] **Step 8: Run tests, expect green**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor && uv run pytest -x
```

Expected: all tests pass. `test_core_vale.py` mocks `subprocess.run`, so the new arg doesn't break it. `test_workflow.py` patches `STYLE_DIR` directly via `@patch("auto_docs_editor.workflow.STYLE_DIR")`, so the path move is invisible to it.

If a test fails referencing the old `style/` path, inspect — it likely needs no edit because mocks shadow the real path.

- [ ] **Step 9: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add -A
git commit -m "refactor: relocate style assets into docs-style plugin tree

- git mv style/ → docs-style/skills/docs-style/references/style/
- git mv vale_styles/ → docs-style/skills/docs-style/vale_styles/
- git mv .vale.ini → docs-style/skills/docs-style/.vale.ini
- Update settings.STYLE_DIR; add settings.VALE_CONFIG
- Pass --config=\$VALE_CONFIG to vale subprocess in core_vale.py"
```

Expected: commit succeeds. `git log --stat -1` shows ~20 file renames + 2 modifications.

---

## Task 3: Add plugin manifest

**Goal:** Create `docs-style/.claude-plugin/plugin.json`.

**Files:**
- Create: `docs-style/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin.json**

Create `/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/.claude-plugin/plugin.json`:

```json
{
  "name": "docs-style",
  "version": "0.1.0",
  "description": "Apply Google Developer Documentation Style Guide to markdown via staged edits + vale lint sweep",
  "author": {
    "name": "Ricardo Decal",
    "email": "biz@ricardodecal.com"
  },
  "repository": "https://github.com/<OWNER>/docs-style",
  "license": "MIT",
  "keywords": ["documentation", "style-guide", "google", "vale", "markdown"]
}
```

Replace `<OWNER>` with the GitHub username captured in Task 1 Step 2.

- [ ] **Step 2: Validate JSON**

```bash
python -c "import json; json.load(open('/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/.claude-plugin/plugin.json'))" && echo OK
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add docs-style/.claude-plugin/plugin.json
git commit -m "feat(docs-style): add plugin manifest"
```

---

## Task 4: Add `vale_check.sh` wrapper

**Goal:** Thin bash script that vale-checks a doc using the plugin's `.vale.ini`.

**Files:**
- Create: `docs-style/skills/docs-style/scripts/vale_check.sh`

- [ ] **Step 1: Write the script**

Create `/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/skills/docs-style/scripts/vale_check.sh`:

```bash
#!/usr/bin/env bash
# Usage: vale_check.sh <document.md>
#
# Prints vale errors in line format. Always exits 0 (errors are signal,
# not failure — the caller is expected to read stdout and act on findings).
#
# Vale config is co-located at <skill_dir>/.vale.ini and references
# <skill_dir>/vale_styles/Google as its rule bundle.
set -euo pipefail
DOC="${1:?usage: vale_check.sh <document.md>}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec vale --config="${SKILL_DIR}/.vale.ini" --output=line "$DOC" || true
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/skills/docs-style/scripts/vale_check.sh
```

- [ ] **Step 3: Smoke-test the script (skip if vale not installed)**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
echo "# Test heading" > /tmp/vale_smoke.md
echo "We are utilizing this." >> /tmp/vale_smoke.md
./docs-style/skills/docs-style/scripts/vale_check.sh /tmp/vale_smoke.md
rm /tmp/vale_smoke.md
```

Expected (when vale installed): zero or more `Google.We` / `Google.Wordlist` line-format errors printed to stdout. Exit code 0 either way.

If vale is not installed: shell error from missing binary; that's acceptable for this step. Note in the commit body that the smoke test was skipped.

- [ ] **Step 4: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add docs-style/skills/docs-style/scripts/vale_check.sh
git commit -m "feat(docs-style): add vale_check.sh wrapper"
```

---

## Task 5: Add SKILL.md

**Goal:** Write the skill description + process discipline for Claude.

**Files:**
- Create: `docs-style/skills/docs-style/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/skills/docs-style/SKILL.md`:

````markdown
---
name: docs-style
description: Use when user wants to apply the Google Developer Documentation Style Guide to a markdown file or asks to "fix doc style", "edit docs", "review for style guide", "make this match Google style". Applies 16 curated style rules in staged passes with user approval between rounds, then runs vale for a mechanical lint sweep.
---

# Apply Google Developer Documentation Style Guide

## When to use

Trigger this skill when the user asks to apply, enforce, or check the
Google Developer Documentation Style Guide on a markdown file. Common
phrasings: "fix doc style", "edit this for style", "make this follow
the style guide", "google-style this doc".

The skill operates on a single `.md` file at a time.

## Process

1. **Confirm the target file** with the user. Ensure it is a `.md` file
   and exists.

2. **List the 16 curated style rules** at
   `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/references/style/*.md`,
   sorted by filename. The numeric prefixes (`00-`, `01-`, ..., `z-`)
   encode the order in which rules must be applied — earlier rules
   establish baselines that later rules can refine.

3. **For each rule file, in prefix order:**
   - Read the rule file.
   - Read the current state of the target document.
   - Propose edits using the `Edit` tool. Apply **only** the current
     rule's guidance. Do not anticipate later rules.
   - Briefly summarize what changed (one to three sentences).
   - Pause and let the user respond: continue, skip the next rule, or
     abort the whole pass.

4. **After all rules have been applied,** run the vale wrapper for a
   mechanical lint sweep:

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/skills/docs-style/scripts/vale_check.sh <document>
   ```

5. **Read vale's stdout** (line-format errors). For each error, decide
   whether to apply a fix inline using the `Edit` tool, or note it as
   pedantic / false positive and skip. Errors look like:

   ```
   <file>:<line>:<col>:<rule>:<message>
   ```

6. **Print a final summary:**
   - Number of rules applied.
   - Number of vale errors fixed; number ignored as pedantic.
   - Any rules the user explicitly skipped.

## Rule application discipline

- **One rule at a time.** Do not batch rules into a single edit pass.
- **Apply only the current rule.** Resist anticipating later rules — the
  curated ordering exists because edits can interact.
- **Skip code blocks** unless the rule explicitly addresses them. Most
  rule files include a `Do not apply this style guide to code blocks`
  hint at the top.
- **Preserve structure:** headings, link targets, frontmatter, anchors,
  and indentation must be retained.

## Resumption

If the user says "skip through commas", "start from headings", or
similar, find the matching rule file by filename substring and skip
all earlier rules.

## Final-pass mode

If the user says "do a final pass" or "quick sweep", process **only**
rule files whose names end with `+` (the error-prone subset). Skip
all others.

## Error handling

| Condition                          | Behavior                                                        |
|-----------------------------------|-----------------------------------------------------------------|
| Target file missing                | Report, stop.                                                   |
| Target is not `.md`                | Report, stop. Do not attempt other formats.                     |
| `vale` not on `PATH`               | Tell user to install (`brew install vale` / `apt install vale`). Skip vale step; still print summary of staged passes.                                  |
| User aborts mid-pass               | Leave doc in current state; summarize rules applied so far.     |
| Rule conflicts with earlier edits  | Expected — prefix ordering is the resolution. Apply current rule; later rules may revert earlier edits by design.                                       |
| `Edit` tool match failure          | Report the exact failed snippet to the user; ask how to proceed.|

## References

- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/references/style/*.md` — 16 curated rule files
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/scripts/vale_check.sh` — vale wrapper
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/.vale.ini` — vale config
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/vale_styles/Google/` — vale rule bundle
````

- [ ] **Step 2: Validate frontmatter**

```bash
head -5 /home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/skills/docs-style/SKILL.md
```

Expected: starts with `---`, has `name:` and `description:` fields, ends second `---`.

- [ ] **Step 3: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add docs-style/skills/docs-style/SKILL.md
git commit -m "feat(docs-style): add SKILL.md"
```

---

## Task 6: Add plugin README

**Goal:** Minimal install + usage instructions for the plugin.

**Files:**
- Create: `docs-style/README.md`

- [ ] **Step 1: Write README**

Create `/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/README.md`:

```markdown
# docs-style — Claude Code Plugin

Apply the [Google Developer Documentation Style Guide](https://developers.google.com/style)
to markdown files via Claude Code, in staged passes with user approval
between rounds, plus a final mechanical [Vale](https://vale.sh/) lint
sweep.

## Install

From the repo root containing this plugin:

```bash
claude plugin install ./docs-style
```

(Adjust the path if installing from a clone elsewhere on disk.)

## Use

In a Claude Code session, ask:

- "Fix the style on `path/to/doc.md`"
- "Apply Google style guide to README.md"
- "Do a final pass on `docs/article.md`"

Claude activates the `docs-style` skill, applies 16 curated style rules
in prefix order, pauses between rounds for review, and ends with a vale
lint sweep.

## Requirements

- Claude Code
- [Vale](https://vale.sh/) on `PATH` for the lint sweep step (optional —
  the skill skips this step gracefully if vale is missing)

## Layout

- `skills/docs-style/SKILL.md` — workflow + discipline
- `skills/docs-style/references/style/` — 16 curated style rule files
- `skills/docs-style/scripts/vale_check.sh` — vale wrapper
- `skills/docs-style/.vale.ini` + `vale_styles/Google/` — vale config + rules

## License

MIT.
```

- [ ] **Step 2: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add docs-style/README.md
git commit -m "docs(docs-style): add plugin README"
```

---

## Task 7: Rename Python pkg dir + console scripts

**Goal:** Rename `auto_docs_editor/` → `docs_style/`, update every Python import, the distribution name, both console scripts, `main.py`, root `README.md`, and tests. One commit, tests must pass at end.

**Files:**
- Move: `auto_docs_editor/` → `docs_style/`
- Modify: `pyproject.toml`, `main.py`, `README.md` (root), `tests/conftest.py`, `tests/test_*.py` (multiple), `docs_style/cli.py`, `docs_style/tui.py`, `docs_style/controller.py`, `docs_style/core_vale.py`, `docs_style/core.py` (and any other `*.py` containing the old name)

- [ ] **Step 1: `git mv` the package directory**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git mv auto_docs_editor docs_style
```

Expected: `git status -s` shows ~10 `R` entries for files under `auto_docs_editor/` → `docs_style/`.

- [ ] **Step 2: Update `pyproject.toml`**

Edit `/home/ricardo/src/PERSONAL/auto_docs_editor/pyproject.toml`. Change:

```toml
[project]
name = "auto_docs_editor"
```
→
```toml
[project]
name = "docs-style"
```

And:

```toml
[project.scripts]
auto-docs-edit = "auto_docs_editor.cli:main"
auto-docs-tui = "auto_docs_editor.tui:run"
```
→
```toml
[project.scripts]
docs-style-edit = "docs_style.cli:main"
docs-style-tui = "docs_style.tui:run"
```

- [ ] **Step 3: Find-replace `auto_docs_editor` → `docs_style` across `*.py`**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
grep -rln 'auto_docs_editor' --include="*.py" \
  | grep -v __pycache__ | grep -v archive \
  | xargs sed -i 's/auto_docs_editor/docs_style/g'
```

Verify:
```bash
grep -rn 'auto_docs_editor' --include="*.py" /home/ricardo/src/PERSONAL/auto_docs_editor/ \
  | grep -v __pycache__ | grep -v archive
```
Expected: no output.

- [ ] **Step 4: Find-replace console script names in markdown + main.py**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
grep -rln 'auto-docs-edit\|auto-docs-tui' --include="*.md" --include="*.py" \
  | grep -v "docs/superpowers" | grep -v __pycache__ \
  | xargs sed -i 's/auto-docs-edit/docs-style-edit/g; s/auto-docs-tui/docs-style-tui/g'
```

Verify:
```bash
grep -rn 'auto-docs-edit\|auto-docs-tui' \
  --include="*.py" --include="*.md" /home/ricardo/src/PERSONAL/auto_docs_editor/ \
  | grep -v "docs/superpowers" | grep -v __pycache__
```
Expected: no output.

- [ ] **Step 5: Update `main.py` docstring + comments**

Inspect `/home/ricardo/src/PERSONAL/auto_docs_editor/main.py`. Change:

```python
"""Main entry point for auto_docs_editor.
```
→
```python
"""Main entry point for docs-style.
```

(Should already be picked up by Step 3's sed — verify with `head main.py`.)

- [ ] **Step 6: Update root `README.md` plugin reference**

Add a top-level section to `/home/ricardo/src/PERSONAL/auto_docs_editor/README.md` immediately after the title. Use the `Edit` tool to insert:

```markdown
## Claude Code plugin

This repo also ships a Claude Code plugin at [`docs-style/`](./docs-style/)
that applies the same curated rules without the Python pipeline. See
[`docs-style/README.md`](./docs-style/README.md) for install + usage.
```

(Place after the existing `# AutoDocsEditor` heading and before
`## Quick start`.)

- [ ] **Step 7: Verify all rename targets gone**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
grep -rn 'auto_docs_editor\|auto-docs-edit\|auto-docs-tui' \
  --include="*.py" --include="*.toml" --include="*.md" \
  | grep -v __pycache__ | grep -v archive | grep -v "docs/superpowers"
```

Expected: no output. (Spec/plan files in `docs/superpowers/` retain old
names as historical reference and are excluded.)

- [ ] **Step 8: Reinstall package so console scripts repoint**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor && uv sync
```

Expected: `uv sync` re-resolves and re-registers `docs-style-edit` and `docs-style-tui` console scripts.

- [ ] **Step 9: Run full test suite**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor && uv run pytest
```

Expected: all tests pass. If any test fails because a `patch("auto_docs_editor.X")` string was missed by sed, fix it inline (sed should have caught these — Step 3 already swept `*.py` files, including tests).

- [ ] **Step 10: Smoke-test console scripts**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
uv run docs-style-edit --help 2>&1 | head -5
uv run docs-style-tui --help 2>&1 | head -5
```

Expected: usage / help output prints without import errors. The old script names should now be unrecognized:

```bash
uv run auto-docs-edit --help 2>&1 | head -3
```
Expected: `error: Failed to spawn: ...auto-docs-edit` or similar.

- [ ] **Step 11: Commit**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git add -A
git commit -m "refactor: rename Python pkg + console scripts to docs-style

- git mv auto_docs_editor/ → docs_style/
- pyproject: name=docs-style, scripts docs-style-{edit,tui}
- Update all Python imports, test patches, README, main.py"
```

Expected: commit succeeds. `git log --stat -1` shows ~25 file modifications + the package rename.

---

## Task 8: Final regression run + plugin smoke test

**Goal:** Confirm everything works end-to-end before pushing.

**Files:** none (verification only).

- [ ] **Step 1: Full test suite**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor && uv run pytest -v
```

Expected: all tests pass with no warnings about unresolved imports.

- [ ] **Step 2: Confirm plugin tree structure**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
find docs-style -type f -not -path '*/vale_styles/*' -not -path '*/references/*' | sort
```

Expected output:
```
docs-style/.claude-plugin/plugin.json
docs-style/README.md
docs-style/skills/docs-style/.vale.ini
docs-style/skills/docs-style/SKILL.md
docs-style/skills/docs-style/scripts/vale_check.sh
```

And:
```bash
ls docs-style/skills/docs-style/references/style/ | wc -l
```
Expected: `16`.

- [ ] **Step 3: Plugin smoke install (manual)**

In a separate Claude Code session:

```bash
claude plugin install /home/ricardo/src/PERSONAL/auto_docs_editor/docs-style
```

Expected: install succeeds. The exact command may differ depending on installed Claude Code version — fall back to consulting `claude plugin --help`.

- [ ] **Step 4: Trigger test (manual)**

In a fresh Claude Code session, on a small test markdown file:

> "Apply google style to /tmp/test.md"

Expected: Claude activates the `docs-style` skill, lists the 16 rules, and proposes the first rule's edits.

- [ ] **Step 5: Vale step test (manual, requires vale installed)**

Run the vale wrapper directly:

```bash
echo "We are utilizing this thing." > /tmp/vale_smoke.md
/home/ricardo/src/PERSONAL/auto_docs_editor/docs-style/skills/docs-style/scripts/vale_check.sh /tmp/vale_smoke.md
rm /tmp/vale_smoke.md
```

Expected: vale prints one or more `Google.*` line-format errors. Exit code 0.

- [ ] **Step 6: Commit (only if any fixups landed during smoke testing)**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git status
```

If anything changed during smoke testing (unlikely):
```bash
git add -A
git commit -m "fix: post-smoke-test fixups"
```

Otherwise: skip.

---

## Task 9: GitHub repo rename

**Goal:** Rename the GitHub repo from `auto_docs_editor` to `docs-style` and update the local clone's remote URL. Local clone parent directory is **not** renamed (would break the active session).

**Files:** none (remote operation + git config edit).

- [ ] **Step 1: Rename the repo on GitHub**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
gh repo rename docs-style --yes
```

Expected: `✓ Renamed repository <owner>/auto_docs_editor to <owner>/docs-style`. The remote URL of the local clone may auto-update — verify in Step 2.

- [ ] **Step 2: Verify remote URL points at the new name**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git remote -v
```

Expected: both `fetch` and `push` URLs end with `/docs-style.git`. If they still show `/auto_docs_editor.git`:

```bash
git remote set-url origin <new url>
```

Replace `<new url>` with `git@github.com:<owner>/docs-style.git` (SSH) or `https://github.com/<owner>/docs-style.git` (HTTPS), matching whatever transport the existing URL used.

- [ ] **Step 3: Test remote connectivity**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git fetch origin
```

Expected: clean fetch, no errors.

- [ ] **Step 4: Push the implementation**

```bash
cd /home/ricardo/src/PERSONAL/auto_docs_editor
git push origin main
```

Expected: push succeeds. The new commits from Tasks 2–7 land on `main`.

---

## Self-review notes

Coverage check — every spec section has a corresponding task:

| Spec section                                      | Plan task(s)        |
|---------------------------------------------------|---------------------|
| Architecture / plugin tree                         | Tasks 2–6           |
| `.claude-plugin/plugin.json`                       | Task 3              |
| SKILL.md                                           | Task 5              |
| `vale_check.sh`                                    | Task 4              |
| `.vale.ini` move + `StylesPath`                    | Task 2              |
| Single-source-of-truth (style/, vale_styles/)      | Task 2              |
| Naming consolidation (Python pkg + scripts)        | Task 7              |
| Settings/path edits (`STYLE_DIR`, `VALE_CONFIG`)   | Task 2              |
| `core_vale.py` `--config` flag                     | Task 2              |
| Repo-wide find-replace                             | Task 7              |
| GitHub repo rename                                 | Task 9              |
| Testing / regression                               | Tasks 1, 2, 7, 8    |
| Vale `--config` pre-flight verification            | Task 1              |

Placeholder scan: `<OWNER>` in `plugin.json` is a deliberate fill-in
referencing Task 1 Step 2's captured value. Not a placeholder failure
because the value source is explicit. `<new url>` in Task 9 Step 2 is
likewise contingent on the captured remote transport — concrete
substitution rule given.

Type/symbol consistency: `STYLE_DIR` (existing), `VALE_CONFIG` (new,
introduced in Task 2 Step 6, used in Task 2 Step 7) — names match across
tasks. Skill name `docs-style`, plugin name `docs-style`, package name
`docs_style` — distinct contexts (skill, plugin, Python module) but
consistent within each. Console script names `docs-style-edit` /
`docs-style-tui` consistent across `pyproject.toml`, `main.py`, README.
