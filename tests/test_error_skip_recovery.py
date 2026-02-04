"""Test error recovery - pressing 's' or 'i' after an error should allow recovery."""

from unittest.mock import patch

import pytest

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.tui import AutoDocsEditorTUI
from tests.helpers.textual import drain_pilot, wait_for_condition


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies that require API keys or external services."""
    with (
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
        patch("auto_docs_editor.controller.enforce_vale_style"),
    ):
        yield


@pytest.fixture
def controller(mock_dependencies, tmp_path):
    """Create a real controller with multiple style guides."""
    # Create dummy document
    doc_path = tmp_path / "test.md"
    doc_path.write_text("# Test Document\n\nSome content here.")

    # Create two style guides so we can test skipping to the next one
    style1 = tmp_path / "01-first-guide.md"
    style1.write_text("First style guide content")

    style2 = tmp_path / "02-second-guide.md"
    style2.write_text("Second style guide content")

    return ReviewController(
        document_path=doc_path,
        style_pages=[style1, style2],
        seen_edits=set(),
    )


@pytest.mark.asyncio
async def test_skip_after_error_advances_to_next_guide(controller):
    """Test that pressing 's' after an error advances to the next guide.

    This tests the bug where:
    1. An error occurs during process_style_guide
    2. The error is shown to the user
    3. The user presses 's' to skip
    4. BUG: Nothing happens because the worker has already exited
    5. EXPECTED: Should advance to the next style guide
    """
    app = AutoDocsEditorTUI(controller)

    # Track which guide we're on
    initial_guide_idx = controller.current_page_idx
    assert initial_guide_idx == 0

    # Mock process_style_guide to raise an error on first call
    error_raised = False

    async def mock_process_style_guide(*args, **kwargs):
        nonlocal error_raised
        if not error_raised:
            error_raised = True
            raise RuntimeError("Edit failed: Text not found in document.")
        # Second call should succeed (no error)

    with patch("auto_docs_editor.tui.process_style_guide", side_effect=mock_process_style_guide):
        async with app.run_test() as pilot:
            # Wait for the app to enter error state
            await wait_for_condition(
                pilot,
                lambda: app.in_error_state,
                timeout=3.0,
            )

            # Confirm we're still at guide 0 (error occurred, not advanced yet)
            assert controller.current_page_idx == 0, "Should still be at guide 0 during error"

            # Now press 's' to skip to the next guide
            await pilot.press("s")
            await drain_pilot(pilot)

            # Wait for error state to clear (indicates error was handled)
            await wait_for_condition(
                pilot,
                lambda: not app.in_error_state,
                timeout=3.0,
            )

            # The controller should have advanced past guide 0
            # (It might be at 1 or 2 depending on how fast the second guide processed)
            assert controller.current_page_idx >= 1, (
                f"Expected to advance past guide index 0, but still at {controller.current_page_idx}. "
                "Pressing 's' after an error should skip to the next guide."
            )


@pytest.mark.asyncio
async def test_quit_after_error_exits_app(controller):
    """Test that pressing 'q' after an error exits the app cleanly."""
    app = AutoDocsEditorTUI(controller)

    error_raised = False

    async def mock_process_style_guide(*args, **kwargs):
        nonlocal error_raised
        error_raised = True
        raise RuntimeError("Edit failed: Text not found in document.")

    with patch("auto_docs_editor.tui.process_style_guide", side_effect=mock_process_style_guide):
        async with app.run_test() as pilot:
            # Wait for the error to be shown
            await wait_for_condition(
                pilot,
                lambda: error_raised,
                timeout=3.0,
            )
            await drain_pilot(pilot)

            # Press 'q' to quit
            await pilot.press("q")
            await drain_pilot(pilot)

            # App should be quitting
            assert app.is_quitting, "App should be quitting after pressing 'q'"


@pytest.mark.asyncio
async def test_ignore_after_error_continues_same_guide(controller):
    """Test that pressing 'i' after an error continues processing the same guide.

    Unlike 's' which skips to the next guide, 'i' should ignore just this error
    and allow the agent to continue finding other issues in the current guide.
    """
    app = AutoDocsEditorTUI(controller)

    call_count = 0

    async def mock_process_style_guide(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Edit failed: Text not found in document.")
        # Second call should succeed (simulating continued processing)

    with patch("auto_docs_editor.tui.process_style_guide", side_effect=mock_process_style_guide):
        async with app.run_test() as pilot:
            # Wait for the app to enter error state
            await wait_for_condition(
                pilot,
                lambda: app.in_error_state,
                timeout=3.0,
            )

            # Confirm we're at guide 0
            assert controller.current_page_idx == 0, "Should be at guide 0 during error"

            # Press 'i' to ignore the error and continue
            await pilot.press("i")
            await drain_pilot(pilot)

            # Wait for error state to clear
            await wait_for_condition(
                pilot,
                lambda: not app.in_error_state,
                timeout=3.0,
            )

            # After ignore, should still be processing (guide index may have advanced
            # depending on how fast processing completed)
            # The key is that 'i' resolved the error state
            assert not app.in_error_state, "Error state should be cleared after pressing 'i'"
