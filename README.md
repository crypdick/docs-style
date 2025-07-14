# Automatic Google Style Formatter

`iterative_style.py` is a script that walks a Markdown document through every page of Google’s developer style guide (stored locally in the `style/` directory) and lets an LLM propose minimal edits until all the style edits have been made.

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

## Incident logs

If an edit fails to apply (e.g. the snippet isn’t found) the script records a log file under `incidents/` so you can inspect what went wrong.
