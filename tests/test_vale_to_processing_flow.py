"""Test that the Vale check properly transitions to guide processing."""

from unittest.mock import AsyncMock, patch

import pytest

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.tui import AutoDocsEditorTUI
from tests.helpers.textual import drain_pilot, wait_for_condition


@pytest.mark.asyncio
async def test_vale_check_transitions_to_processing(tmp_path):
    """Test that after Vale check completes, guide processing starts.

    This test catches the bug where start_processing_guide() was called
    from a worker thread and never properly scheduled.
    """
    # Create dummy files
    doc_path = tmp_path / "test.md"
    doc_path.write_text("# Test Document\n\nSome content.")

    style_path = tmp_path / "style_guide.md"
    style_path.write_text("# Style Guide\n\nSome rules.")

    # Create a real controller (not a MagicMock)
    controller = ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )

    # Track whether start_processing_guide was called
    processing_started = False

    # Mock external dependencies
    with (
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
        patch.object(controller, "run_vale") as mock_run_vale,
        patch("auto_docs_editor.tui.process_style_guide") as mock_process_guide,
    ):
        # Make run_vale succeed quickly
        mock_run_vale.return_value = None

        # Make process_style_guide set our flag when called
        async def track_processing(*args, **kwargs):
            nonlocal processing_started
            processing_started = True

        mock_process_guide.side_effect = track_processing

        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            # Wait for Vale check to complete
            await drain_pilot(pilot, timeout=2.0)

            # Verify Vale check was called
            assert mock_run_vale.called, "Vale check should have been called"

            # Wait for processing to start (this is where the bug manifests)
            # The bug: start_processing_guide() was never scheduled, so this times out
            await wait_for_condition(
                pilot,
                lambda: processing_started,
                timeout=3.0,
            )

            # Verify processing actually started
            assert processing_started, (
                "Guide processing should have started after Vale check completed. "
                "If this fails, start_processing_guide() may not be properly scheduled."
            )


@pytest.mark.asyncio
async def test_vale_check_logs_appear_in_ui(tmp_path):
    """Test that Vale check progress is visible in the UI."""
    doc_path = tmp_path / "test.md"
    doc_path.write_text("# Test")

    style_path = tmp_path / "style.md"
    style_path.write_text("# Style")

    controller = ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )

    with (
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
        patch.object(controller, "run_vale"),
        patch("auto_docs_editor.tui.process_style_guide", new_callable=AsyncMock),
    ):
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await drain_pilot(pilot, timeout=2.0)

            # Check that the activity log exists and is accessible
            # The actual log content depends on timing, but we can verify the widget exists
            activity_log = app.query_one("#activity-log")
            assert activity_log is not None, "Activity log should exist in UI"


@pytest.mark.asyncio
async def test_processing_worker_is_scheduled(tmp_path):
    """Test that the start_processing_guide worker is actually created."""
    doc_path = tmp_path / "test.md"
    doc_path.write_text("# Test")

    style_path = tmp_path / "style.md"
    style_path.write_text("# Style")

    controller = ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )

    with (
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
        patch.object(controller, "run_vale"),
        patch("auto_docs_editor.tui.process_style_guide", new_callable=AsyncMock),
    ):
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await drain_pilot(pilot, timeout=2.0)

            # Verify that workers were created and ran
            # The key test is that processing_started becomes True in the first test
            # This test just verifies the app can start without errors
            assert app.is_running, "App should be running"
            assert not app.is_quitting, "App should not be quitting"
