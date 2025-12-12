import asyncio
from unittest.mock import patch

import pytest
from textual.widgets import TextArea

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.tui import AutoDocsEditorTUI
from auto_docs_editor.widgets import RejectionModal

# --- Helpers ---


async def drain_pilot(pilot, timeout: float = 1.0) -> None:
    """Wait for Textual's message queue (and any BaseScreen workers) to settle."""
    await pilot.pause()
    try:
        screen = getattr(pilot.app, "screen", None)
    except Exception:
        screen = None
    wait_for_workers = getattr(screen, "wait_for_workers_idle", None)
    if callable(wait_for_workers):
        try:
            await wait_for_workers(timeout=timeout)
        except TimeoutError:
            pass


async def wait_for_condition(pilot, predicate, timeout: float = 2.0) -> None:
    """Poll for a condition without sprinkling raw pilot.pause() loops everywhere."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await drain_pilot(pilot, timeout=max(timeout, 0.5))
    raise AssertionError("Timed out waiting for condition")


# --- Test ---


@pytest.mark.asyncio
async def test_rejection_ui_update_race(tmp_path):
    """
    Verifies that the UI correctly updates to the next proposal after a rejection with reason,
    handling the race condition where the modal dismissal might overlap with the next proposal.
    """
    doc_path = tmp_path / "test.md"
    doc_path.write_text("Original Content")
    style_path = tmp_path / "style_guide.md"
    style_path.write_text("Style guide content")

    # Mock process_style_guide to simulate two sequential reviews
    async def mock_process_style_guide(style_text, session, callbacks, review_callback, guide_name):
        # First proposal
        decision1 = await review_callback(
            before="Original Content", after="First Proposal", reason="Reason 1"
        )
        assert decision1["status"] == "rejected"
        assert decision1["reason"] == "My Reason"

        # IMMEDIATE next proposal to trigger potential race with modal dismissal
        await review_callback(before="Original Content", after="Second Proposal", reason="Reason 2")

    with (
        patch("auto_docs_editor.tui.process_style_guide", side_effect=mock_process_style_guide),
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
            # 1. Wait for first proposal
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal is not None
                and app.current_proposal[1] == "First Proposal",
            )

            # 2. Reject
            await pilot.press("r")

            # 3. Wait for modal
            await wait_for_condition(pilot, lambda: isinstance(app.screen, RejectionModal))

            # 4. Interact with modal
            reason_input = app.screen.query_one("#reason-input", TextArea)
            reason_input.load_text("My Reason")

            # 5. Confirm rejection
            await pilot.click("#confirm")

            # 6. Wait for second proposal in state
            await wait_for_condition(
                pilot,
                lambda: app.current_proposal is not None
                and app.current_proposal[1] == "Second Proposal",
            )

            # 7. Check if UI updated using safe query
            def check_ui_text():
                try:
                    # Look for the text area on the main screen
                    # The fix ensures we wait for modal to close, so we should be on main screen
                    if isinstance(app.screen, RejectionModal):
                        return False
                    ta = app.query_one("TextArea.edit-area", TextArea)
                    return ta.text == "Second Proposal"
                except Exception:
                    return False

            await wait_for_condition(pilot, check_ui_text)
