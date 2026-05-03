from unittest.mock import AsyncMock, patch

import pytest

from docs_style.controller import ReviewController
from docs_style.tui import AutoDocsEditorTUI
from tests.helpers.textual import drain_pilot


@pytest.mark.asyncio
async def test_ask_user_review_thread_safety(tmp_path):
    """
    Regression test: Ensure ask_user_review handles being called from the main thread
    without raising 'call_from_thread method must run in a different thread' error.
    """
    # Create real files and controller to avoid MagicMock issues
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello World")
    style_path = tmp_path / "style_guide.md"
    style_path.write_text("Style guide content")

    controller = ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )

    # Mock dependencies and checks that require API keys
    with (
        patch("docs_style.tui.process_style_guide"),
        patch("docs_style.tui.get_langfuse_handler", return_value=None),
        patch("docs_style.controller.enforce_vale_style"),
        patch("docs_style.tui.logger.error") as mock_error,
    ):
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await drain_pilot(pilot)

            # Mock review_event.wait to avoid hanging - we just want to test
            # that ask_user_review can be called without thread safety errors
            app.review_event.wait = AsyncMock()

            await app.ask_user_review("before", "after", "reason")

            # Verify no thread-related errors were logged
            found = False
            for call in mock_error.call_args_list:
                msg = str(call[0][0])
                if "Error checking active screen" in msg:
                    found = True
                    break

            assert not found, (
                f"Found error log indicating call_from_thread misuse: {mock_error.call_args_list}"
            )
