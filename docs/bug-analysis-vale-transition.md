# Bug Analysis: Vale Check to Processing Transition Failure

## Summary

The TUI was getting stuck on "Running initial Vale check..." even though the Vale check completed successfully in the background. The UI never progressed to showing style guide processing.

## Root Cause

In `auto_docs_editor/tui.py`, the `run_initial_vale_check()` method is decorated with `@work(exclusive=True, thread=True)`, meaning it runs in a background thread. At the end of this method, it was calling:

```python
self.start_processing_guide()
```

However, `start_processing_guide()` is an async method decorated with `@work`, which needs to be properly scheduled on the main event loop. Calling it directly from a worker thread doesn't properly schedule it as a worker, so it was never executing.

## The Fix

Changed the code to use `call_from_thread()` to properly schedule the next step on the main thread:

```python
# After Vale check, start processing guides from the main thread
self.call_from_thread(self._start_processing_after_vale)

def _start_processing_after_vale(self) -> None:
    """Helper to start processing from main thread after Vale check."""
    self.start_processing_guide()
```

This ensures that `start_processing_guide()` is called from the main thread context, allowing it to be properly scheduled as an async worker.

## Why Tests Didn't Catch This

### 1. Over-Mocking with MagicMock

The default `controller` fixture in `conftest.py` uses `MagicMock`:

```python
@pytest.fixture
def controller():
    controller = MagicMock()
    controller.is_finished = False
    controller.current_guide_path = None
    controller.progress_str = "0/0"
    return controller
```

**Problem**: `MagicMock` automatically succeeds for any method call, including `controller.run_vale()`. The test doesn't catch that `start_processing_guide()` is never properly scheduled because the mock doesn't exercise the real threading/async behavior.

**Lesson**: Use real objects in integration tests, or at least use `Mock` with explicit method definitions instead of `MagicMock`.

### 2. Insufficient Assertions in Startup Test

The `test_app_startup` test only checks that the app doesn't crash:

```python
async def test_app_startup(app):
    async with app.run_test() as pilot:
        assert app.is_running
        await drain_pilot(pilot)
        # Checks for worker errors but not for progression
```

**Problem**: The test doesn't verify that the app actually progresses through its initialization sequence. It only checks that nothing crashes.

**Lesson**: Integration tests should verify the complete happy path, not just absence of errors.

### 3. No Integration Test for Vale → Processing Flow

There was no test that verified the complete flow:
1. Vale check runs
2. Vale check completes
3. Guide processing starts
4. UI updates appropriately

**Problem**: Each component was tested in isolation, but the transition between components wasn't tested.

**Lesson**: Always test state transitions and handoffs between components.

## New Test Coverage

Added `test_vale_to_processing_flow.py` with three tests:

1. **`test_vale_check_transitions_to_processing`**: Verifies that after Vale check completes, guide processing actually starts. This would have caught the bug.

2. **`test_vale_check_logs_appear_in_ui`**: Verifies that Vale check progress is visible to the user.

3. **`test_processing_worker_is_scheduled`**: Verifies that the `start_processing_guide` worker is actually created and scheduled.

## Key Takeaways

1. **Avoid over-mocking**: Use real objects when testing integration points
2. **Test state transitions**: Don't just test that components work in isolation
3. **Test threading/async boundaries**: These are common sources of bugs
4. **Verify the happy path completely**: Don't just check for absence of errors
5. **Use real controllers in TUI tests**: The `MagicMock` hides real behavior

## Related Files

- Fixed: `auto_docs_editor/tui.py` (lines 398-421)
- New tests: `tests/test_vale_to_processing_flow.py`
- Test infrastructure: `tests/conftest.py` (controller fixture)
