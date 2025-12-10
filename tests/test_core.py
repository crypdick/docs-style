from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auto_docs_editor.core import DocumentSession, handle_edit_proposal, process_style_guide


def test_document_session_apply_edit():
    content = "Hello world"
    session = DocumentSession(content, set())

    # Successful edit
    result = session.apply_edit("world", "universe")
    assert "Edit applied successfully" in result
    assert session.current_content == "Hello universe"
    assert ("world", "universe") in session.session_edits

    # Failed edit (not found) -> Should raise RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        session.apply_edit("foobar", "baz")

    assert "not found in document" in str(excinfo.value)
    assert len(session.failed_edits) == 1


@pytest.mark.asyncio
async def test_handle_edit_proposal_non_interactive():
    content = "Hello world"
    session = DocumentSession(content, set())

    # Successful
    result = await handle_edit_proposal(session, "world", "universe", "reason")
    assert "Edit applied successfully" in result
    assert session.current_content == "Hello universe"

    # Failed -> Should raise RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        await handle_edit_proposal(session, "foo", "bar", "reason")
    assert "not found in document" in str(excinfo.value)


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


@pytest.mark.asyncio
async def test_process_style_guide_escapes_braces():
    """Test that style guides with curly braces are escaped to prevent prompt template errors."""
    session = DocumentSession("Some content", set())

    # A style guide with problematic curly braces
    style_guide_with_braces = "Use {choice1|choice2} syntax."

    # Mock all the LangChain and OpenAI internals to avoid actual execution
    with (
        patch("auto_docs_editor.core.ChatOpenAI"),
        patch("auto_docs_editor.core.create_tool_calling_agent") as mock_create_agent,
        patch("auto_docs_editor.core.AgentExecutor") as mock_executor_cls,
        patch("auto_docs_editor.core.ChatPromptTemplate") as mock_prompt_cls,
    ):
        # Setup mocks
        mock_executor = MagicMock()
        # ainvoke is awaited, so it must be an AsyncMock or return a coroutine
        mock_executor.ainvoke = AsyncMock(return_value="done")
        mock_executor_cls.return_value = mock_executor

        # Run the function
        await process_style_guide(style_guide_with_braces, session)

        # Verify ChatPromptTemplate.from_messages was called
        assert mock_prompt_cls.from_messages.called

        # Get the arguments passed to from_messages
        args, _ = mock_prompt_cls.from_messages.call_args
        messages = args[0]

        # Find the system message
        system_msg = next((msg[1] for msg in messages if msg[0] == "system"), None)
        assert system_msg is not None

        # Check that braces were escaped
        assert "Use {{choice1|choice2}} syntax." in system_msg
        assert "Use {choice1|choice2} syntax." not in system_msg
