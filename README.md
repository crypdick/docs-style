# Automatic Google Style Formatter

`iterative_style.py` is a script that walks a Markdown document through every page of [Google’s developer style guide](https://developers.google.com/style) (stored locally in the `style/` directory) and lets an LLM propose minimal edits until all the style edits have been made.

This makes the process of hand-checking a long document against dozens of individual style pages less tedious.

## Quick start

```bash
# Export your OpenAI key (or put it in a .env file)
export OPENAI_API_KEY="sk-..."

# Run against a Markdown doc
uv run --script iterative_style.py docs/your_article.md
```

The script pauses in between each set of edits to give you the opportunity to review the changes. When you’re happy with the result you can commit them and resume the script. The script itself never touches git.

Note: this script was tested with "gpt-4.1-mini", but it made too many mistakes. Switching to "o4-mini" improved the results.

### Skipping ahead

If you’ve already applied some pages you can jump forward:

```bash
uv run --script iterative_style.py \
    --skip-through commas.md docs/your_article.md
```

This skips every style page **up to and including** `commas.md`.

You can also press the `ESC` key to skip the current style page.

## Incident logs

If an edit fails to apply (e.g. the snippet isn’t found) the script records a log file under `incidents/` so you can inspect what went wrong.

## Differences to the official style guide

- I moved some guides that are irrlevant for my use-case to `archive/`.
- I deleted Google- and Android-specific style guides.
- I simplified some style guides to make them more "atomic" and less monolithic.
- Added a few LLM hints to prevent common LLM mistakes while applying the style guides, e.g. "Do not apply this style guide to code blocks."
- Added a few style precidence rules to enforce an ordering of the style guides.
- Dropped preference for `_` over `*` for italics.
- Added some personal style guides. These are prefixed with `PERSONAL-`.

## Style precidence

The order in which the style guides are applied is important, because future edits may revert previous edits. The default order is alphabetic. Therefore, in order to enforce an ordering, you can add prefixes to the style guide names. The prefixes `00-`, `01-`, `02-`, will be applied in that order, before non-numeric style guides. Conversely, `z-` will be applied last.