from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_ask_user_review_thread_safety(app):
    """
    Regression test: Ensure ask_user_review handles being called from the main thread
    without raising 'call_from_thread method must run in a different thread' error.
    """
    with patch("auto_docs_editor.tui.logger.error") as mock_error:
        async with app.run_test() as pilot:
            # Just calling the method directly from the main thread
            # This simulates what happens when start_processing_guide (async worker on main loop) calls it.

            # We need to wrap it in a try/except because if the second call_from_thread (lines 175/178)
            # triggers and IS NOT guarded (if threading.get_ident() mismatch or AttributeError), it might raise.
            # But likely in this test setup, threading.get_ident() matches, so it goes to line 173 (direct call).
            # So only the FIRST call_from_thread (line 160) should fail and be caught.

            # Note: ask_user_review awaits review_event.wait(). We need to set it or the test will hang.
            # We can schedule a task to set the event, or just rely on timeout/mocking?
            # Or we can just let it hang? No, we need it to return or at least reach the error point.
            # The error point is BEFORE the wait.

            # But if it waits, the test will hang.
            # We can mock review_event.wait to return immediately.

            app.review_event.wait = AsyncMock()

            await app.ask_user_review("before", "after", "reason")

            found = False
            for call in mock_error.call_args_list:
                msg = str(call[0][0])
                if "Error checking active screen" in msg:
                    found = True
                    break

            assert not found, (
                f"Found error log indicating call_from_thread misuse: {mock_error.call_args_list}"
            )
