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

2. **List the curated style rules** at
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

If the user says "start from lists", "skip through wordlist", or
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

- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/references/style/*.md` — curated rule files (apply in prefix order)
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/scripts/vale_check.sh` — vale wrapper
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/.vale.ini` — vale config
- `${CLAUDE_PLUGIN_ROOT}/skills/docs-style/vale_styles/Google/` — vale rule bundle
