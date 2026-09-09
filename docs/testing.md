# Testing

Run the test suite from the repository root:

```shell
uv run pytest -n 2
```

Tests use temporary documents and mock external LLM and Vale calls. No API key,
Langfuse account, or Vale installation is needed. The shared fixture supplies a
dummy OpenAI key and removes Langfuse credentials.

For a focused failure, run the relevant module in one process:

```shell
uv run pytest tests/test_core.py -n 0
```

The pytest configuration supplies a five-second timeout and parallel execution
by default. Use `-n` to choose a worker count appropriate to the machine.

## Coverage

- `test_core.py`, edit scenarios, and context tests cover document replacement,
  review decisions, whitespace matching, and surrounding context.
- `test_core_vale.py` covers Vale findings, execution failures, retry limits,
  and rejected full-document responses.
- `test_workflow.py` covers setup, target loading, and guide selection, including
  discovery of the actual bundled resources.
- `test_notebook.py` covers Jupytext pairing and synchronization.
- TUI tests cover startup, review actions, immediate writes, guide transitions,
  and recovery after an error or skip.

## TUI tests

Use a real `ReviewController` for workflow integration tests and mock the external
operations at their boundaries. A controller supplied to the shared `app` fixture
must be defined by the test module. Avoid a blanket `MagicMock` controller when
asserting state transitions: its truthy attributes can hide incorrect behavior.

Run interactions inside `async with app.run_test() as pilot:`. The helpers in
[tests/helpers/textual.py](../tests/helpers/textual.py) provide key presses,
clicks, and message-queue draining. Use `wait_for_condition` to wait for an
observable state change; a drained UI queue does not prove that every background
worker has finished.

The initial Vale check runs in a worker thread. Its handoff to guide processing
must go through `call_from_thread()` to schedule work on the UI thread.
[test_vale_to_processing_flow.py](../tests/test_vale_to_processing_flow.py)
checks that processing actually begins after Vale completes.

Keep test documents and mutable state local to each test. If a failure occurs
only in parallel, inspect shared state and worker cleanup before adding delays
or grouping tests.

## Other checks

Run the configured formatting and file checks:

```shell
uvx pre-commit run --all-files
```

To check the bundled Vale configuration when Vale is installed:

```shell
bash skills/docs-style/scripts/vale_check.sh README.md
```

Vale findings require editorial review; a lint suggestion is not automatically
a useful edit. Changes to prompts or the skill also need a representative manual
review because mocked LLM tests do not measure editing quality.
