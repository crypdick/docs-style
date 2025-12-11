# Testing Textual Applications

Comprehensive guide to testing Textual TUI applications.

## Decision Tree

```
Need to test UI rendering or user interaction?
├─ YES → Use `async with app.run_test() as pilot:`
│         Always use `await pilot.pause()` after interactions
└─ NO  → Instantiate directly, call methods, assert results
```

---

## Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_screen_integration(app, dm_fake):
    # Setup data
    dm_fake.create_task("Task", project_id="test-project-1",
                       due={"date": date.today().isoformat()})

    async with app.run_test() as pilot:
        app.push_screen("my_screen")
        await pilot.pause()  # Wait for mount & reactive updates

        # Simulate interaction
        await pilot.press("down")
        await pilot.pause()

        # Assert
        screen = pilot.app.screen
        assert screen.query_one(ListView).index > 0

        # Exit cleanup (for screens with background workers)
        await app.pop_screen()
        await pilot.pause()
```

---

## Unit Test Pattern

```python
def test_screen_logic():
    """Test logic without UI."""
    screen = MyScreen()
    screen.tasks = [{"id": "1"}]
    result = screen._compute_filtered()
    assert len(result) == 1
```

---

## pilot.pause() Guidelines

> **Note:** The [official Textual docs](https://textual.textualize.io/guide/testing/#pausing-the-pilot) say pausing is "generally not required." With background workers and parallel tests, we've found it's essential.

**Always use default `await pilot.pause()`** — it waits for Textual's message queue to drain:

```python
# ✅ Good: Batch actions, single pause
await pilot.press("down")
await pilot.press("enter")
await pilot.pause()  # Waits for queue to drain

# ❌ Avoid: Hardcoded delays
await pilot.pause(0.1)  # Less reliable
```

**Exit cleanup for screens with workers:**

```python
async with app.run_test() as pilot:
    review_btn.press()
    await pilot.pause()
    assert isinstance(pilot.app.screen, SuggestionReviewScreen)

    # Ensure clean teardown
    await app.pop_screen()
    await pilot.pause()  # Let mount/unmount complete
```

Without this final pause, parallel tests (`pytest -n32`) crash with "worker not properly terminated."

---

## Centralized Pilot Helpers

Import shared helpers from `tests/helpers/textual.py` instead of re-implementing:

```python
from tests.helpers.textual import (
    drain_pilot,
    press_and_drain,
    push_screen_and_drain,
    focus_and_drain,
)
```

**Helper benefits:**

- `drain_pilot()` wraps `pilot.pause()` **and** waits for `BaseScreen.wait_for_workers_idle()` when available
- `press_and_drain()` / `push_screen_and_drain()` bundle interaction + pause (satisfies `check-polling` hook)
- `focus_and_drain()` standardizes "focus widget, let Textual settle" pattern
- Single source of truth: changes propagate everywhere automatically

**Background worker tests:**

A single `pause()` after mount waits for the message queue to drain (including worker completion):

```python
async with app.run_test() as pilot:
    app.push_screen("daily_dash")
    await pilot.pause()  # Waits for mount + worker messages

    assert len(screen.query_one("#tasks", ListView).children) > 0
```

---

## Testing Blocking Modal Flows

When testing an action that `awaits` a modal result (e.g., `await screen.wait_for_dismiss()`), calling that action directly will **block the test indefinitely**.

**Solution: Use `asyncio.create_task`**

```python
import asyncio

# 1. Trigger the action in the background
task = asyncio.create_task(screen.action_triggering_modal())

# 2. Let event loop turn so modal pushes
await pilot.pause()

# 3. Interact with modal
assert isinstance(pilot.app.screen, ModalScreen)
await pilot.click("#confirm-btn")
await pilot.pause()

# 4. Verify action completed
await task  # Should be done now
```

### Avoiding Deadlocks in Navigation Tests

If a test hangs indefinitely when a button is pressed, verify how the application pushes the new screen. If an event handler `awaits` a screen push (which waits for that screen to close), it blocks the message pump, preventing the test pilot from interacting with the new screen.

**Fix:** Use `run_worker` in the application code to push screens without blocking the handler.

```python
# ❌ Bad: Blocks handler until screen closes (causes test deadlocks)
async def on_button_pressed(self):
    # This suspends the message loop until DetailScreen pops!
    await self.app.push_screen(DetailScreen())

# ✅ Good: Non-blocking (test friendly)
def on_button_pressed(self):
    # Spawns a worker to handle the wait, freeing the message loop
    self.run_worker(self.app.push_screen(DetailScreen()))
```

### Worker Crashes and "Node Down" Errors

If you see `[gw1] node down: Not properly terminated` or silent crashes during parallel tests:

1. **Unhandled Exceptions in Workers:**
    Textual workers that crash with unhandled exceptions (like `TypeError` or `beartype` violations) can cause the pytest-xdist worker to terminate abruptly without printing the traceback.

2. **Debugging Strategy:**
    Run the specific test **without parallelization** (`-n0`) and with **output enabled** (`-s`) to see the actual exception.

    ```bash
    # Reveal the hidden exception
    uv run pytest -n0 -s tests/path/to/test.py::test_name
    ```

3. **Common Causes:**
    - Passing Pydantic models where dicts are expected (causing type hint violations).
    - Missing `await` in async handlers.
    - Infinite recursion in properties or `compose()`.

### Reliable Modal Results

In integration tests, `await app.push_screen(screen)` might sometimes return `None` unexpectedly or race with the worker result. A robust pattern in application code is to push the screen and then explicitly await its dismissal.

```python
# ✅ Robust Pattern
await self.app.push_screen(screen)
result = await screen.wait_for_dismiss()
```

---

## Testing Screens with Long-Running Workers

Standard helpers like `drain_pilot()` or `wait_for_workers_idle()` wait for **all** active workers to complete. This creates deadlocks with persistent background workers (e.g., infinite polling loops).

See: [Textual Workers Guide](https://textual.textualize.io/guide/workers/) for background on how workers function.

**The Problem:**

`wait_for_workers_idle()` blocks until `_active_workers` is empty. If a worker runs forever (until screen unmounts), this helper never returns, causing test timeouts.

**Solutions:**

### 1. Avoid Blocking Waits

Use `wait_for_predicate` to poll for specific UI state changes:

```python
# ✅ Good: Poll for UI side-effect without waiting for worker exit
await wait_for_condition(
    pilot,
    lambda: len(screen.query(Select)) > 0,
    timeout=2.0
)
```

### 2. Mock the Worker Logic

Mock the underlying service so the worker completes immediately:

```python
with patch("my_screen.PollingAgent") as MockAgent:
    # Mock returns immediately, worker finishes
    ...
```

### 3. Explicit Cleanup

Use `try...finally` to ensure screen pops even if assertions fail:

```python
try:
    await wait_for_predicate(...)
finally:
    if isinstance(app.screen, MyScreen):
        await app.pop_screen()
        await pilot.pause()
```

**For loops that push multiple screens:**

```python
# ❌ Flaky: Screens accumulate, workers crash
async with app.run_test() as pilot:
    for screen_name in ["daily_dash", "settings", "weekly_dash"]:
        await push_screen_and_drain(app, pilot, screen_name)
        # Test something...
        await press_and_drain(pilot, "escape")  # Might not properly clean up workers

# ✅ Reliable: Explicit cleanup in finally block
async with app.run_test() as pilot:
    for screen_name in ["daily_dash", "settings", "weekly_dash"]:
        try:
            await push_screen_and_drain(app, pilot, screen_name)
            # Test something...
        finally:
            # Ensure screen is popped for proper worker cleanup
            if len(app._screen_stack) > 1:
                await app.pop_screen()
                await pilot.pause()  # Critical: allows workers to terminate
```

## `screen_session`: built-in cleanup helper

`tests/helpers/textual.py` exposes `screen_session(app, pilot, screen)` which wraps
the reliable pattern above in an async context manager:

```python
from tests.helpers.textual import screen_session

async with app.run_test() as pilot:
    for screen_name in ["daily_dash", "settings", "weekly_dash"]:
        async with screen_session(app, pilot, screen_name):
            # Interact with widgets safely
            await press_and_drain(pilot, "f")
            ...
```

Using `screen_session` ensures every temporary screen is popped and its workers have
time to shut down even when the test fails midway through the context. This prevents
parallel `pytest -n32` jobs from crashing with the dreaded “worker not properly
terminated” error.

### Handling tests that mock navigation helpers

Some button-heavy suites (e.g., “press every button” tests) mock `app.push_screen` /
`app.pop_screen` / `app.switch_screen` so button handlers cannot navigate away during the
assertion. When those helpers are replaced with no-ops, `screen_session` can no longer rely
on Textual’s pop hooks to shrink the stack. To keep worker cleanup deterministic:

- Always apply navigation mocks *inside* the `screen_session` block and restore the original
  methods before the context exits.
- `reset_screen_stack()` now falls back to trimming `app._screen_stack` manually whenever it
  detects mocked helpers. This ensures xdist workers still see the stack return to the root
  screen, even if a test forgot to restore the original methods.

```python
async with app.run_test() as pilot:
    async with screen_session(app, pilot, my_screen):
        orig_push = app.push_screen
        try:
            app.push_screen = lambda *_a, **_kw: MockAwaitComplete()
            # run button assertions…
        finally:
            app.push_screen = orig_push
```

> **Fail-safe:** the shared `app` fixture patches `run_test()` to call
> `reset_screen_stack()` whenever a test exits the context. That safety net force-pops any
> leaked screens back to the root and drains outstanding worker cancellations. It keeps
> pytest workers alive even if a test forgets to use `screen_session`, but you should still
> wrap each screen interaction in the helper so the test remains deterministic and
> debuggable.

**Why this matters:**

- Pressing "escape" might navigate away, but doesn't guarantee worker cleanup
- Without `await pilot.pause()` after `pop_screen()`, workers don't finish cancellation
- Parallel tests (`pytest -n32`) crash with "worker not properly terminated"

---

### 4. Prefer Push-Driven Updates Over Pollers

Most "workers never finish" bugs come from **polling**: one worker loads data, while a
second worker loops forever waiting for the first worker's result. The fix is usually to
eliminate the poller and let the loader update the UI directly.

- Have the data-fetching worker call `update_ui_callback()` (or set a reactive) as soon
  as it receives data.
- Avoid background loops that merely check `manager.suggestions` or similar flags.
- Tests become deterministic because `_active_workers` empties as soon as the loader
  finishes, so `drain_pilot()` does not hang.

Think "push updates when you know something changed" instead of "poll until it looks
different."

---

### 5. Avoid Looping Over Screens in Tests

**Problem:** Tests that loop over multiple screens in a single test case can cause worker
crashes in parallel execution, even when using `screen_session` for cleanup.

```python
# ❌ Bad: Loop over screens in single test
async def test_hotkey_on_all_screens(app):
    screens = ["daily_dash", "evening_review", "weekly_dash", "settings"]
    async with app.run_test() as pilot:
        for screen_name in screens:
            async with screen_session(app, pilot, screen_name):
                await press_and_drain(pilot, "f")
                assert app.is_running
```

**Why it fails:**

- Rapidly pushing/popping 4+ screens in a loop creates timing issues in parallel execution
- Workers from previous screens may not fully terminate before next screen mounts
- `screen_session` cleanup helps but doesn't eliminate the race condition
- In parallel test runs (pytest -n auto), multiple workers doing this simultaneously causes crashes

**Solution: Use `@pytest.mark.parametrize`**

```python
# ✅ Good: Each screen gets its own test case
@pytest.mark.parametrize("screen_name", ["daily_dash", "evening_review", "weekly_dash", "settings"])
async def test_hotkey_on_all_screens(app, screen_name):
    async with app.run_test() as pilot:
        async with screen_session(app, pilot, screen_name):
            await press_and_drain(pilot, "f")
            assert app.is_running
```

**Benefits:**

- Each screen test runs independently (better isolation)
- Parallel execution distributes screen tests across workers (no single worker overload)
- Failures are easier to debug (shows which specific screen failed)
- No rapid screen cycling within a single test

**Note:** This issue occurred even with proper `screen_session` cleanup, suggesting that
the cleanup helper alone isn't sufficient when rapidly cycling through many screens. The
real fix is to avoid the loop pattern entirely by using parameterization.

---

## Fixing Flaky Parallel Tests

Tests that pass when run alone but fail randomly in parallel execution (with `pytest -n auto`) indicate race conditions or timing issues.

> **If you see errors like** `worker 'gw12' crashed while running ...` or
> `worker not properly terminated`, jump to the sections above on `screen_session`
> and `reset_screen_stack()`. Those crash messages almost always mean a screen stayed
> mounted, a worker never cancelled, and xdist killed the process. The cleanup helper
> fixes that class of failure.

### Diagnosing Flaky Tests

**Step 1: Confirm flakiness**

```bash
# Run test 20 times and count outcomes
for i in {1..20}; do
    uv run pytest tests/test_file.py::test_name -q --tb=no 2>&1 | tail -1
done | sort | uniq -c

# Output shows flakiness:
#   12 1 passed in 5.40s
#    8 1 failed in 5.65s
```

**Step 2: Isolate the issue**

```bash
# Test individual parametrizations
uv run pytest 'tests/test_file.py::test_name[param1]' -v --count=10

# Test without parallelization
uv run pytest tests/test_file.py -n0  # Usually passes
```

### Common Causes and Solutions

#### 1. Race Condition: Screen Not Fully Mounted

**Problem:** Interacting with screen before mount completes

```python
# ❌ Flaky: Might click before button exists
await app.push_screen(MyScreen())
await pilot.pause()
await pilot.click("#button")  # Race condition!
```

**Solution:** Add `drain_pilot()` + verify initial state

```python
# ✅ Reliable: Wait for mount + verify state
await app.push_screen(MyScreen())
await pilot.pause()
await drain_pilot(pilot)  # Wait for mount + workers

# Verify initial state (fails fast if something's wrong)
screen = pilot.app.screen
assert isinstance(screen, MyScreen)
assert len(screen.items) == expected_count
assert screen.current_index == 0

# Now safe to interact
await pilot.click("#button")
```

#### 2. Checking Stale State After Interaction

**Problem:** Asserting against captured screen reference that doesn't update

```python
# ❌ Flaky: screen reference might be stale
screen = pilot.app.screen
await pilot.click("#next-btn")
await pilot.pause()
assert screen.current_index == 1  # Checks old object
```

**Solution:** Use `wait_for_condition` with fresh state lookup

```python
# ✅ Reliable: Polls for actual state change
await pilot.click("#next-btn")
await pilot.pause()

await wait_for_condition(
    pilot,
    lambda: pilot.app.screen.current_index == 1,  # Fresh lookup each time
    timeout=2.0
)
```

#### 3. Tests Interfering in Parallel Execution

**Problem:** Multiple test instances modifying shared state or timing-sensitive screens

**Solution:** Use `xdist_group` marker to run tests sequentially on same worker

```python
# At module level - all tests in file run on same worker
pytestmark = pytest.mark.xdist_group(name="button_interaction_tests")

# Or on individual test
@pytest.mark.xdist_group(name="screen_state_tests")
async def test_stateful_interaction(app):
    ...
```

**When to use:**

- Tests pushing/popping screens rapidly
- Tests with timing-sensitive interactions
- Tests sharing resources (even via fixtures)

**Register marker in pyproject.toml:**

```toml
[tool.pytest.ini_options]
markers = [
    "serial: mark test to run serially (not in parallel)",
]
```

#### 4. Complex Custom Fixtures

**Problem:** Custom app fixtures with extra cleanup causing worker crashes

```python
# ❌ Can cause worker crashes
@pytest.fixture
async def custom_app():
    app = PersonalProjectManagerApp()
    # Complex patching/cleanup
    ...
```

**Solution:** Use standard `app` fixture; add synchronization in test instead

```python
# ✅ Use standard fixture + explicit waits in test
async def test_interaction(app):  # Standard fixture
    await app.push_screen(MyScreen())
    await pilot.pause()
    await drain_pilot(pilot)  # Explicit synchronization
    ...
```

### Complete Pattern: Reliable Button Interaction Test

```python
import pytest
from tests.helpers.textual import drain_pilot, wait_for_condition

# Mark module to avoid parallel interference
pytestmark = pytest.mark.xdist_group(name="button_tests")

@pytest.mark.asyncio
async def test_button_advances_to_next_item(app):
    """Clicking Next button should advance to next item."""

    async with app.run_test() as pilot:
        # 1. Push screen and wait for full mount
        await app.push_screen(MyScreen(items=["A", "B", "C"]))
        await pilot.pause()
        await drain_pilot(pilot)

        # 2. Verify initial state (fails fast if broken)
        screen = pilot.app.screen
        assert isinstance(screen, MyScreen)
        assert len(screen.items) == 3
        assert screen.current_index == 0
        assert screen.current_item == "A"

        # 3. Interact
        await pilot.click("#next-btn")
        await pilot.pause()

        # 4. Wait for state change (not blind pause)
        await wait_for_condition(
            pilot,
            lambda: pilot.app.screen.current_index == 1,
            timeout=2.0
        )

        # 5. Assert final state
        assert pilot.app.screen.current_item == "B"
```

### Systematic Debugging Checklist

When a test is flaky:

- [ ] Run 10-20 times to confirm and measure failure rate
- [ ] Test without parallelization (`-n0`) to confirm it's a race condition
- [ ] Add `drain_pilot()` after screen mount/push
- [ ] Add early assertions to verify initial state
- [ ] Replace `assert state` checks after interaction with `wait_for_condition()`
- [ ] Use `lambda: pilot.app.screen.property` (not captured screen reference)
- [ ] Add `xdist_group` marker if tests share timing-sensitive resources
- [ ] Remove custom fixtures; use standard `app` fixture + explicit waits
- [ ] Check logs for "worker not terminated" → missing cleanup or infinite workers

---

## Test Data Requirements

Use **relative dates** and **valid project IDs** from pillar hierarchy:

```python
# ✅ Good
dm_fake.create_task("Task",
                   project_id="test-project-1",
                   due={"date": date.today().isoformat()})

# ❌ Bad: Hardcoded date gets filtered out
dm_fake.create_task("Task", due={"date": "2024-01-01"})
```

---

## CSS in Test Subclasses

When creating test-specific screen subclasses, explicitly set `CSS_PATH = None`. Otherwise, Textual attempts to load CSS relative to the test file's directory, causing `StylesheetError`.

```python
class TestLoadingScreen(BaseScreen):
    SCREEN_NAME = "test_loading"
    CSS_PATH = None  # ✅ Prevent looking for base_screen.tcss in tests/
```

---

## Common Test Errors

| Error | Fix |
|-------|-----|
| Empty UI in tests | `await pilot.pause()` + use valid `project_id` |
| StylesheetError | Set `CSS_PATH = None` in test subclasses |
| Node down / worker not terminated | Ensure `app.pop_screen()` cleanup OR Check for unhandled exceptions in workers (run with `-n0 -s`) |
| Test blocks indefinitely | Use `asyncio.create_task` for modal tests |
| Timeout with polling workers | Use `wait_for_condition` instead of `drain_pilot()` |
| Flaky test (passes alone, fails in parallel) | Add `drain_pilot()` after mount + use `wait_for_condition()` + add `xdist_group` marker |
| Stale state after interaction | Use `lambda: pilot.app.screen.property` not captured screen reference |
| Worker crashes with screen loops | Use `@pytest.mark.parametrize` instead of looping over screens in test |
| Deadlock when pushing screen | Use `self.run_worker(self.app.push_screen(...))` in app code |

---

## Resources

- **Textual Testing Guide**: <https://textual.textualize.io/guide/testing/>
- **Textual Workers Guide**: <https://textual.textualize.io/guide/workers/>
- **Test Fixtures Documentation**: `tests/fixtures/README.md` (400+ lines with examples)
- **Testing README**: `tests/README.md` (comprehensive testing philosophy)
- **Pilot Helpers**: `tests/helpers/textual.py`
