# AutoDocsEditor

`AutoDocsEditor` makes your documentation conform to the [Google Developer Documentation Style Guide](https://developers.google.com/style) by using *large language models* (*LLMs*). This is a large style guide, so the `AutoDocsEditor` breaks up the job into stages, proposing incremental edits to a document. This makes the process of hand-checking a long document against dozens of individual style rules less tedious.

## Quick start

Export your OpenAI key (or put it in a `.env` file):

```bash
export OPENAI_API_KEY="sk-..."
```

Run `auto_docs_edit.py` against a target Markdown document:


```bash
uv run --script auto_docs_edit.py docs/your_article.md
```

This script processes the Markdown file against every page of the style guide (stored locally in the `style/` directory). The script pauses between each set of edits, giving you the opportunity to review the proposed edits and commit the incremental changes before moving on to the next set of style rules. The script itself never touches Git.

Note: for best results, use `o4-mini`.

### Skip style rules

If you are resuming a run, you can skip style rules you have already processed:

```bash
uv run --script auto_docs_edit.py \
    --skip-through commas.md docs/your_article.md
```

This example skips every style rule **up to and including** `commas.md`.

You can also press the `ESC` key to interrupt the current task and skip to the next task.

### Final pass sweep

After you have iterated through the full style-guide once and made additional manual edits, you can run a **quick compliance sweep** over only the most error-prone rules:

```bash
uv run --script auto_docs_edit.py --final-pass docs/your_article.md
```

The script will process **only** those style-guide pages whose filenames end with a `+` (for example `01-lists+.md` or `commas-serial+.md`).

## Incident logs

If an edit fails to apply (for example, the script cannot find the snippet), the script records a log file under `incidents/` so you can inspect what went wrong.

## Differences to the official style guide

- Moved some guides that are irrelevant for my use-case to `archive/`.
- Deleted Google- and Android-specific style rules.
- Simplified some style rules to make them more "atomic" and less monolithic.
- Added a few LLM hints to prevent common LLM mistakes while applying the style guides, e.g. "Do not apply this style guide to code blocks."
- Added a few style precedence rules to enforce an ordering of the style guides.
- Dropped preference for `_` over `*` for italics.
- Removed internal links between style rule pages, since the LLM applies one set of style rules at a time and also can't follow the links.
- Added some personal style rules. These personal style rules are prefixed with `PERSONAL-`.

## Set style rule precedence

The order in which the style rules are applied is important, because subsequent edits may revert previous edits. The default order is alphabetic. Therefore, to enforce an ordering, you can add prefixes to the style guide names. The script applies the prefixes `00-`, `01-`, `02-` in that order, before non-numeric style guides. Conversely, the script applies `z-` last.

# Planned features

- [ ] Support for applying the script to Jupyter notebooks.
- [ ] Expose reasoning for each edit.
