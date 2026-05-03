import asyncio
from unittest.mock import patch

import pytest
from textual.widgets import TextArea

from docs_style.controller import ReviewController
from docs_style.tui import AutoDocsEditorTUI
from tests.helpers.textual import drain_pilot, press_and_drain, wait_for_condition

# Run these tests serially to avoid timing issues with UI mounting
pytestmark = pytest.mark.xdist_group(name="tui_concurrency_tests")


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

    # Mock dependencies and checks that require API keys
    with (
        patch("docs_style.tui.process_style_guide"),
        patch("docs_style.tui.get_style_guides", return_value=[style_path]),
        patch("docs_style.tui.load_and_validate_target"),
        patch("docs_style.tui.setup_logging"),
        patch("docs_style.tui.get_langfuse_handler", return_value=None),
        patch("docs_style.controller.enforce_vale_style"),
    ):
        controller = ReviewController(
            document_path=doc_path,
            style_pages=[style_path],
            seen_edits=set(),
        )
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await drain_pilot(pilot)

            # Define two concurrent review tasks
            async def review_1():
                return await app.ask_user_review("Original", "Change 1", "Reason 1")

            async def review_2():
                # Yield control to ensure review_1 grabs lock first
                await drain_pilot(pilot)
                return await app.ask_user_review("Original", "Change 2", "Reason 2")

            # Launch both tasks
            task1 = asyncio.create_task(review_1())
            task2 = asyncio.create_task(review_2())

            # Wait for first proposal to appear
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal is not None and app.current_proposal[1] == "Change 1",
                timeout=2.0,
            )

            # Accept the first proposal
            await press_and_drain(pilot, "a")

            # Wait for task 1 to complete
            result1 = await task1
            assert result1["status"] == "accepted"

            # Wait for second proposal to appear
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal[1] == "Change 2",
                timeout=2.0,
            )

            # Accept the second proposal
            await press_and_drain(pilot, "a")

            result2 = await task2
            assert result2["status"] == "accepted"


@pytest.mark.asyncio
async def test_user_edits_are_preserved_with_concurrency(tmp_path):
    """
    Verifies that if a user edits the proposal during a concurrent storm,
    the edit is correctly returned for the active proposal.
    """
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Hello World")
    style_path = tmp_path / "style_guide.md"
    style_path.write_text("Style guide content")

    # Mock dependencies and checks that require API keys
    with (
        patch("docs_style.tui.process_style_guide"),
        patch("docs_style.tui.get_style_guides", return_value=[style_path]),
        patch("docs_style.tui.load_and_validate_target"),
        patch("docs_style.tui.setup_logging"),
        patch("docs_style.tui.get_langfuse_handler", return_value=None),
        patch("docs_style.controller.enforce_vale_style"),
    ):
        controller = ReviewController(
            document_path=doc_path,
            style_pages=[style_path],
            seen_edits=set(),
        )
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            await drain_pilot(pilot)

            async def review_1():
                return await app.ask_user_review("Original", "Change 1", "Reason 1")

            async def review_2():
                # Yield control to ensure review_1 grabs lock first
                await drain_pilot(pilot)
                return await app.ask_user_review("Original", "Change 2", "Reason 2")

            task1 = asyncio.create_task(review_1())
            task2 = asyncio.create_task(review_2())

            # Wait for first proposal to appear
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal is not None and app.current_proposal[1] == "Change 1",
                timeout=2.0,
            )

            # Wait for DiffView's TextArea to be mounted
            def text_area_mounted():
                try:
                    return len(app.query("TextArea.edit-area")) > 0
                except Exception:
                    return False

            await wait_for_condition(pilot, text_area_mounted, timeout=2.0)

            # User edits the text area
            text_area = app.query_one("TextArea.edit-area", TextArea)
            text_area.load_text("Change 1 Modified")

            # Accept the modified proposal
            await press_and_drain(pilot, "a")

            result1 = await task1
            # Should be modified since user changed the text
            assert result1["status"] == "modified"
            assert result1["new_text"] == "Change 1 Modified"

            # Wait for second proposal to appear
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal[1] == "Change 2",
                timeout=2.0,
            )

            # User accepts Change 2 as is
            await press_and_drain(pilot, "a")

            result2 = await task2
            assert result2["status"] == "accepted"
