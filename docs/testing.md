# Testing

Run the test suite from the repository root:

```shell
uv run pytest -n 2
```

Tests use temporary documents and mock external large language model (LLM) and
Vale calls. You don't need an API key, Langfuse account, or system-wide Vale installation.
The shared fixture supplies a placeholder OpenAI API key and removes Langfuse credentials.

To investigate a failure, run the relevant test module in one process:

```shell
uv run pytest tests/test_core.py -n 0 --no-cov
```

The pytest configuration supplies a five-second timeout and parallel execution
by default. Use `-n` to choose a worker count appropriate to the machine.

## Coverage

The suite covers these behaviors:

- `test_core.py`, edit scenarios, and context tests cover document replacement,
  review decisions, whitespace matching, and surrounding context.
- `test_core_vale.py` covers Vale findings, execution failures, retry limits,
  and rejected full-document responses.
- `test_vale_requirement.py` covers missing Vale, wrapper configuration discovery,
  file-specific configuration paths, bundled fallback, and failure propagation
  with a temporary Vale stub.
- `test_workflow.py` covers setup, target loading, and guide selection, including
  discovery of the actual bundled resources.
- `test_notebook.py` covers Jupytext pairing and synchronization.
- Terminal user interface (TUI) tests cover startup, review actions, immediate
  writes, guide transitions, and recovery after an error or skip.

## TUI tests

Use a real `ReviewController` for workflow integration tests and mock the external
operations at their boundaries. In the test module, define any controller that
you supply to the shared `app` fixture. Avoid a blanket `MagicMock` controller when
asserting state transitions: its truthy attributes can hide incorrect behavior.

Run interactions inside `async with app.run_test() as pilot:`. The helpers in
[tests/helpers/textual.py](../tests/helpers/textual.py) provide key presses,
clicks, and message-queue draining. Use `wait_for_condition` to wait for an
observable state change. A drained TUI queue does not prove that every background
worker has finished.

The initial Vale check runs in a worker thread. Its handoff to guide processing
must go through `call_from_thread()` to schedule work on the TUI thread.
[test_vale_to_processing_flow.py](../tests/test_vale_to_processing_flow.py)
checks that guide processing begins after Vale completes.

Keep test documents and mutable state local to each test. If a failure occurs
only in parallel, inspect shared state and worker cleanup before adding delays
or grouping tests.

## Other checks

Run the configured formatting and file checks:

```shell
uv run prek run --all-files
```

Run the Vale wrapper with the required project dependency:

```shell
uv run --locked bash skills/docs-style/scripts/vale_check.sh README.md
```

The wrapper prefers the nearest `.vale.ini` file in the document's directory or
an ancestor directory. Without one, it uses the bundled configuration. It ignores
global configuration and preserves file-specific project settings.

Check rule behavior with the locked Vale executable:

```shell
uv run --locked python scripts/check_vale_rules.py
```

This deterministic check runs real Vale against regression fixtures. It's
separate from the default pytest suite, which mocks external tool calls.

Vale findings require editorial review. A lint suggestion is not automatically
a useful edit. Changes to prompts or the skill also need a representative manual
review because mocked LLM tests do not measure editing quality.

## Fresh environments and worktrees

Install Python 3.12 or later and uv, then run:

```shell
uv sync --locked
uv run --locked vale --version
uv run prek install
uv run prek run --all-files
```

If you have installed the `new-feature` command-line tool,
`new-feature create NAME --no-agent`
creates an isolated worktree and runs the setup configured in `pyproject.toml`.
Replace `NAME` with the name of your feature.
Tests need no `.env` file. Provide credentials locally only for interactive editing.
Each checkout keeps its own `.venv`, logs, test cache, and coverage artifacts.
The shared uv download cache is content-addressed.

## Quality gates

The `prek.toml` configuration file runs Vale, file hygiene and secret checks, Ruff,
pyupgrade, flynt, strict mypy, Vulture, deptry, source policy checks, and tests.
Continuous integration (CI) runs the same command on Python 3.12 and 3.13.
The standalone maintenance scripts declare their dependencies inline. Ruff checks
these scripts, but mypy and deptry exclude them. Tests are outside mypy scope.

Setup downloads the locked Vale executable on first use. The Vale hook checks
maintained Markdown files with the bundled rules. Missing executables and
configuration failures fail the hook. Style findings remain subject to editorial
review. Unit tests mock Vale or use temporary stub executables and do not download
or run the real binary.

Branch coverage includes the full `docs_style` package, including entry points.
The enforced floor is 70%. Raise `fail_under` in `[tool.coverage.report]` as
coverage improves toward 100%. The coverage report shows missing lines
in the terminal and in the `htmlcov/index.html` file. Do not omit
uncovered production modules or lower the floor to pass a change.

For a focused run that does not measure the whole package, use `--no-cov` as in
the example at the start of this page.

The secrets baseline contains audited false positives only. Review each finding
before updating it. Never accept actual credentials into the baseline. Run scans
with `--no-verify` to prevent the scanner from sending candidate credentials over the network.

When changing settings, command-line behavior, resource paths,
or prompts, check the corresponding [README guidance](../README.md). Review
[Architecture](ARCHITECTURE.md) twice a year and update the
[Quality scorecard](QUALITY.md) after meaningful coverage or scope changes.
