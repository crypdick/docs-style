---
name: docs-style
description: Review or edit Markdown documentation using this repo's curated Google developer documentation style rules and a required Vale lint check. Use for documentation style requests, especially Google style compliance.
---

# Documentation style

Apply the curated rules to the Markdown files in the user's request. For a
review, report findings; for an editing request, make the changes. Ask for a
target only when the request and workspace leave it unclear.

All resource paths in this guide are relative to this skill's directory.

## Required dependency

Vale must be installed and runnable before reviewing or editing documentation.
Check with `vale --version`. In a repository checkout, run `uv sync --locked`
and `uv run --locked vale --version`; use `uv run --locked` before the wrapper
command to run it in that environment. For a standalone skill installation,
follow the [Vale installation instructions](https://docs.vale.sh/topics/installation)
and make `vale` available on `PATH`.

Install the dependency if it is missing. If installation or execution fails,
report the failure and stop; do not skip Vale or claim that the review is complete.

## Review and edit

Read the target document and any applicable repository writing conventions.
Use [references/style/](references/style/) for the curated rules:

- `00-*`: documentation principles, voice, tone, tense, and person.
- `01-*`: headings, paragraphs, lists, terminology, and inclusive language.
- `02-*`: links, notices, procedures, and tables.
- `03-code+.md`: code formatting, command examples, and API documentation.
- `03-wordlist+.md`: vocabulary reference; look up terms used in the document.
- `04-*`: accessibility, filenames, and placeholders.
- `z-grammar-and-language+.md`: grammar and punctuation.

For a full review, cover all applicable topics. For a focused request, read
only the relevant references. Filename order provides a useful progression
from broad editorial choices to mechanics; it does not require separate edit
rounds. Combine related corrections and continue without per-rule approval
unless the user requests staged review.

Preserve meaning, technical claims, and the author's voice. Prefer a small,
useful correction over rephrasing already clear prose. User instructions and
repository conventions take precedence over these defaults. Resolve conflicts
by preserving accuracy and readability, rather than repeatedly undoing edits.

Keep link destinations, reference identifiers, explicit anchors, frontmatter,
and Markdown structure intact. If a heading change affects generated anchors,
check local references. Do not rename existing files, APIs, flags, or literal
values to satisfy a prose rule. Edit code samples only when the relevant rule
addresses their presentation and the change preserves syntax and behavior.

## Optional modes

- **Final pass / quick sweep:** Use the references whose filenames end in
  `+.md`, concentrating on issues that remain after earlier edits.
- **Resume:** “Start from lists” includes the matching reference; “skip through
  wordlist” excludes it and all earlier references. Match filenames and ask
  only if the requested starting point is ambiguous.

## Vale check

Run the bundled wrapper for every target document after editing, or during a
review. Invoke it using the resolved skill directory and an absolute document
path so it works from any working directory:

```shell
bash /path/to/skills/docs-style/scripts/vale_check.sh /absolute/path/to/document.md
```

Replace `/path/to/skills/docs-style` with the absolute path to this skill's
directory and `/absolute/path/to/document.md` with the absolute path to the
document.

The wrapper uses [.vale.ini](.vale.ini) and the bundled
[Google rules](vale_styles/Google/). It reports findings on stdout and uses
`--no-exit` so style findings do not produce a failing exit status. Treat
execution or configuration failures separately from style findings.

Use editorial judgment on each finding; skip suggestions that change meaning,
conflict with the curated rules, or make the prose worse. Recheck after fixes.
Execution and configuration failures block completion until they are resolved.

Summarize the substantive changes or findings, any unresolved issues, and
the Vale result. Avoid a rule-by-rule transcript.
