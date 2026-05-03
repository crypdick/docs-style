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
