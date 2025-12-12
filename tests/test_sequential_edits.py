import pytest

from auto_docs_editor.core import DocumentSession, handle_edit_proposal


@pytest.mark.asyncio
async def test_sequential_edits_with_manual_override():
    """
    Verify that:
    1. A user can modify an agent's proposal.
    2. The session content is updated to the USER'S version.
    3. Subsequent edits can target the text as it exists after the user's modification.
    """
    # Setup a multi-line string to test context expansion properly
    initial_content = """Line 1
Line 2: The target word is HERE.
Line 3
"""
    session = DocumentSession(initial_content, set())

    # --- Step 1: Agent proposes replacing "HERE" with "THERE" ---
    # User decides "THERE" is not good enough, changes it to "GONE"

    async def user_override_callback(before, after, reason):
        # verify what the agent proposed (before/after are expanded context)
        assert "HERE" in before
        assert "THERE" in after

        # The UI would show the user the expanded context (default 3 lines).
        # Since our content is 3 lines, it will grab everything.
        # User edits the text to say "GONE" instead of "THERE"
        modified_text = """Line 1
Line 2: The target word is GONE.
Line 3
"""
        return {"status": "modified", "new_text": modified_text}

    result1 = await handle_edit_proposal(
        session,
        before="HERE",
        after="THERE",
        reason="Fix location",
        review_callback=user_override_callback,
    )

    # Verify the output message reflects the override
    assert "User changed suggested diff to" in result1
    assert "Line 2: The target word is GONE." in result1

    # Verify the document state is updated to "GONE" (User's edit), NOT "THERE" (Agent's proposal)
    expected_content_step1 = """Line 1
Line 2: The target word is GONE.
Line 3
"""
    assert session.current_content == expected_content_step1

    # --- Step 2: Agent (simulated) now wants to change "GONE" to "BACK" ---
    # This verifies that the "document state" used for the next matching is correct.
    # If the session hadn't updated, "GONE" would not be found.

    async def user_accept_callback(before, after, reason):
        # Verify the agent is seeing the "before" correctly as "GONE"
        assert "GONE" in before
        return {"status": "accepted"}

    result2 = await handle_edit_proposal(
        session,
        before="GONE",
        after="BACK",
        reason="Return it",
        review_callback=user_accept_callback,
    )

    assert "User accepted" in result2

    expected_content_step2 = """Line 1
Line 2: The target word is BACK.
Line 3
"""
    assert session.current_content == expected_content_step2
