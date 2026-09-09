# Repository guidance

See `CONVENTIONS.md` for design principles, `docs/ARCHITECTURE.md` for the module
map, and `docs/QUALITY.md` for coverage gaps and check scope.

Use `uv sync --locked` and `uv run prek run --all-files`. Keep dependencies in
`pyproject.toml` and `uv.lock` synchronized through uv commands. Run focused
checks while editing, then the complete hook suite before finishing.

Preserve document meaning and link syntax. Default tests must not call external
LLMs, publish PRs, or require credentials. Keep temporary state per test and
per checkout. Do not lower coverage thresholds or add broad suppressions to
make a failure pass; fix the failure or document a specific boundary exception.
