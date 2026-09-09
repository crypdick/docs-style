# Repository guidance

See [Design conventions](CONVENTIONS.md) for design principles,
[Architecture](docs/ARCHITECTURE.md) for the module map, and
[Quality scorecard](docs/QUALITY.md) for coverage gaps and check scope.

Use `uv sync --locked`, `uv run --locked vale --version`, and
`uv run prek run --all-files`. Keep dependencies in
the `pyproject.toml` and `uv.lock` files synchronized through uv commands. Run focused
checks while editing, then the complete hook suite before finishing.

Preserve document meaning and link syntax. Default tests must not call external
large language models (LLMs), publish pull requests (PRs), or require credentials.
Keep temporary state separate for each test and checkout. Do not lower coverage
thresholds or add broad suppressions to make a failure pass. Fix the failure or
document a specific boundary exception.
