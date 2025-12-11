from pathlib import Path
from unittest.mock import patch

import pytest

from auto_docs_editor.controller import ReviewController
from tests.helpers.textual import drain_pilot


# Mock external dependencies
@pytest.fixture
def mock_dependencies():
    with (
        patch("auto_docs_editor.tui.process_style_guide") as mock_process,
        patch("auto_docs_editor.tui.get_style_guides") as mock_get_guides,
        patch("auto_docs_editor.tui.load_and_validate_target") as mock_load,
        patch("auto_docs_editor.tui.setup_logging"),
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
    ):
        # Setup mocks
        mock_process.return_value = None  # async mock if needed
        mock_get_guides.return_value = [Path("style/00-test-guide.md")]

        yield {
            "process": mock_process,
            "get_guides": mock_get_guides,
            "load": mock_load,
        }


@pytest.fixture
def controller(mock_dependencies, tmp_path):
    """Override the default mock controller with a real one for this test module."""
    # Create dummy files
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello World")

    style_path = tmp_path / "style_guide.md"
    style_path.write_text("Style guide content")

    # Setup controller with mocks
    return ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )


@pytest.mark.asyncio
async def test_app_startup(app):
    """Test that the app starts up without crashing."""

    # Run the app for a short duration to trigger startup events
    async with app.run_test() as pilot:
        # Check if the app is running and mounted
        assert app.is_running

        # Allow some time for workers to start/fail
        # drain_pilot waits for workers to be idle, which is better than hardcoded sleep
        await drain_pilot(pilot)

        # If it crashed, it would have raised an exception by now or app.return_value would be set
        # But run_test suppresses some errors unless we check explicitly or if they bubble up.

        # We can also check if the worker failed.
        # In the traceback, the worker failed with RuntimeError.

        # Let's inspect workers
        for worker in app.workers:
            if worker.name == "start_processing_guide":
                if worker.error:
                    raise worker.error

        assert not app.is_quitting
