---
name: docs-style
description: Review or edit Markdown documentation using this repo's curated Google developer documentation style rules and a required Vale lint check. Use for documentation style requests, especially Google style compliance.
---

# Documentation style

Review or edit the requested Markdown documentation using the
[curated style references](references/style/). Report findings for a review;
apply changes for an editing request. User instructions and repository writing
conventions take precedence over style defaults.

Resource paths below are relative to this skill's directory.

## Vale prerequisite

Vale must be runnable before reviewing or editing. In a repository checkout,
run `uv sync --locked` and `uv run --locked vale --version`; prefix the wrapper
command below with `uv run --locked`. For a standalone installation, check
`vale --version` and follow the [Vale installation instructions](https://docs.vale.sh/topics/installation)
if missing. Installation or execution failure blocks the workflow; report it
rather than skipping Vale.

## Editorial judgment

Read the target and applicable repository conventions. Cover all applicable
style topics for a full review, or select relevant references for a focused
request. Choose the editing order and grouping that suit the document; per-rule
approval is unnecessary unless the user requests it.

Preserve meaning, technical accuracy, and the author's voice. Change clear
prose only when doing so improves it. Keep link destinations, reference
identifiers, explicit anchors, frontmatter, and Markdown structure intact.
Check local references when heading changes affect generated anchors. Do not
rename files, APIs, flags, or literal values for prose style. Change code samples
only for presentation rules and without altering syntax or behavior.

For a final pass or quick sweep, use references ending in `+.md`. When resuming,
include the named reference for "start from" and exclude it and earlier
references for "skip through." Ask only when the target or starting point cannot
be inferred from the request and workspace.

## Vale check

Run the bundled wrapper on every target during a review or after editing.
Use absolute paths so the invocation is independent of the working directory:

```shell
bash /path/to/skills/docs-style/scripts/vale_check.sh \
    /absolute/path/to/document.md
```

The wrapper uses the nearest `.vale.ini` in the document's directory or an
ancestor, preserving file-specific settings. Otherwise, it uses the bundled
[configuration](.vale.ini) and [Google rules](vale_styles/Google/). It ignores
global configuration; a broken project configuration does not trigger fallback.

Style findings do not fail the command (`--no-exit`); execution and configuration
failures block completion. Evaluate findings for accuracy, readability, and
consistency with the curated rules rather than applying them mechanically.
Recheck after fixes.

Summarize substantive changes or findings, unresolved issues, and the Vale result.
