import asyncio
from unittest.mock import patch

import pytest

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.tui import AutoDocsEditorTUI


@pytest.mark.asyncio
async def test_concurrent_reviews_are_serialized(tmp_path):
    """
    Verifies that concurrent calls to ask_user_review are serialized,
    preventing race conditions.
    """
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello World")
    style_path = tmp_path / "style_guide.md"
    style_path.write_text("Style guide content")

    # Mock dependencies
    with (
        patch("auto_docs_editor.tui.process_style_guide"),
        patch("auto_docs_editor.tui.get_style_guides", return_value=[style_path]),
        patch("auto_docs_editor.tui.load_and_validate_target"),
        patch("auto_docs_editor.tui.setup_logging"),
        patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None),
    ):
        controller = ReviewController(
            document_path=doc_path,
            style_pages=[style_path],
            seen_edits=set(),
        )
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Define two concurrent review tasks
            async def review_1():
                return await app.ask_user_review("Original", "Change 1", "Reason 1")

            async def review_2():
                # Yield to ensure review_1 grabs lock first if they start same time
                await asyncio.sleep(0.01)
                return await app.ask_user_review("Original", "Change 2", "Reason 2")

            # Launch both tasks
            task1 = asyncio.create_task(review_1())
            task2 = asyncio.create_task(review_2())

            # Give them time to settle
            await asyncio.sleep(0.1)

            # At this point, review_1 should have the lock and be showing "Change 1".
            # review_2 should be waiting on the lock.

            assert app.current_proposal is not None
            assert app.current_proposal[1] == "Change 1"

            # Accept the first proposal
            await pilot.press("a")

            # Wait a bit for task 1 to finish and task 2 to start
            result1 = await task1
            assert result1["status"] == "accepted"

            await asyncio.sleep(0.1)

            # Now review_2 should be active and showing "Change 2"
            assert app.current_proposal[1] == "Change 2"

            # Accept the second proposal
            await pilot.press("a")

            result2 = await task2
            assert result2["status"] == "accepted"
