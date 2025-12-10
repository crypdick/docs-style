import pytest

from auto_docs_editor.core import DocumentSession, handle_edit_proposal


def test_document_session_apply_edit():
    content = "Hello world"
    session = DocumentSession(content, set())

    # Successful edit
    result = session.apply_edit("world", "universe")
    assert "Edit applied successfully" in result
    assert session.current_content == "Hello universe"
    assert ("world", "universe") in session.session_edits

    # Failed edit (not found)
    result = session.apply_edit("foobar", "baz")
    assert "Edit failed" in result
    assert session.current_content == "Hello universe"
    assert len(session.failed_edits) == 1


@pytest.mark.asyncio
async def test_handle_edit_proposal_non_interactive():
    content = "Hello world"
    session = DocumentSession(content, set())

    # Successful
    result = await handle_edit_proposal(session, "world", "universe", "reason")
    assert "Edit applied successfully" in result
    assert session.current_content == "Hello universe"

    # Failed
    result = await handle_edit_proposal(session, "foo", "bar", "reason")
    assert "Edit failed" in result


@pytest.mark.asyncio
async def test_handle_edit_proposal_interactive_accepted():
    content = "Hello world"
    session = DocumentSession(content, set())

    def callback(before, after, reason):
        return {"status": "accepted"}

    result = await handle_edit_proposal(
        session, "world", "universe", "reason", review_callback=callback
    )
    assert "User accepted" in result
    assert session.current_content == "Hello universe"
    assert session.stats["accepted"] == 1


@pytest.mark.asyncio
async def test_handle_edit_proposal_interactive_rejected():
    content = "Hello world"
    session = DocumentSession(content, set())

    def callback(before, after, reason):
        return {"status": "rejected", "reason": "Nah"}

    result = await handle_edit_proposal(
        session, "world", "universe", "reason", review_callback=callback
    )
    assert "User rejected" in result
    assert session.current_content == "Hello world"
    assert session.stats["rejected"] == 1


@pytest.mark.asyncio
async def test_handle_edit_proposal_interactive_modified():
    content = "Hello world"
    session = DocumentSession(content, set())

    def callback(before, after, reason):
        return {"status": "modified", "new_text": "friend"}

    result = await handle_edit_proposal(
        session, "world", "universe", "reason", review_callback=callback
    )
    assert "User changed suggested diff" in result
    assert session.current_content == "Hello friend"
    assert session.stats["rejected"] == 1  # Modified counts as rejected per logic


@pytest.mark.asyncio
async def test_handle_edit_proposal_noop():
    content = "Hello world"
    session = DocumentSession(content, set())

    # No-op edit: before == after
    result = await handle_edit_proposal(session, "world", "world", "reason")

    # Expect failure
    assert "Edit failed" in result
    assert "identical" in result.lower() or "no changes" in result.lower()

    # Content should be unchanged
    assert session.current_content == "Hello world"
