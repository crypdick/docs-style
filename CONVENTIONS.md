# Design conventions

Run `uv run prek run --all-files` before submitting changes. Tool versions live
in `uv.lock`; manage dependencies with `uv add` and `uv remove`.

## Editing behavior

Preserve technical meaning, Markdown links, reStructuredText (RST) links, and
notebook pairing.
Use `DocumentSession` for edit application and `ReviewController` for review
state. Test observable document changes and review decisions through public
entry points. Mock calls to large language models (LLMs), Vale, and Jupytext in
the default suite.

Vale is a required runtime dependency and skill prerequisite. Missing or failed
Vale execution must stop the workflow. Review style findings with editorial
judgment; do not treat execution failures as an empty findings list.

Parse external data at the boundary. Prefer constrained models or explicit
parsers for LLM decisions and tool output instead of passing unchecked mappings
through the workflow. Use `NewType` when distinct identifiers need static
separation; neither `NewType` nor a frozen dataclass validates input by itself.
Do not wrap ordinary text buffers or counters without a concrete benefit.

## Composition and framework boundaries

Compose workflow behavior through the controller and callbacks. Textual widget
and LangChain callback inheritance are intentional framework contracts.
Keep annotations available to Beartype at run time. Apply `@beartype` below the
Textual `@work` decorator so it checks the underlying function before the worker
wrapper changes its return type. Create LangChain tools from already checked functions.

Use keyword arguments for behavior flags in added APIs. Preserve callback
signatures required by frameworks. Explain narrow linter exemptions where used.
Keep recovery handlers observable with logging or re-raising; catch specific
exceptions for expected failures. Prefer Loguru bindings for structured context
and standard library `extra` mappings in the crawler. Ruff checks print and
logging calls.

## Files and shared state

Name modules after their responsibilities; do not add `utils.py`, `helpers.py`,
or `misc.py`. The existing `utils.py` contains file I/O, logging, and tracing;
extract these into named modules when changing those responsibilities.
Limit Python files to 400 logical lines. Ruff enforces complexity limits.

Keep test files and mutable state in `tmp_path`. Runtime logs, `.env`, virtual
environments, coverage output, and caches belong to the current checkout.
Content-addressed uv caches may be shared. Do not copy credentials into source
control or invent service isolation for this application.

## Documentation and ongoing preferences

Update docs when changing documented behavior. Add a `NOTE:` back-pointer at
code sites with values repeated in prose. See [Architecture](docs/ARCHITECTURE.md)
for the module map and [Quality scorecard](docs/QUALITY.md) for known gaps.

During feature review, compare affected command-line interface (CLI) help,
settings, resource paths, and tests against the README file and testing guidance.
Review the architecture map twice a year and after structural changes.
Correct concrete drift in the same change;
avoid claiming that mocked tests measure LLM editing quality.

When the user states a durable coding preference, enforce it with an existing
tool setting or a focused check when practical. Record judgment-based principles
here. The `.claude/hookify.*.md` files provide reminders when Hookify is present;
they do not install Hookify or replace the mechanical prek checks.
