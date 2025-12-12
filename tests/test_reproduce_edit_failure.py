import pytest

from auto_docs_editor.core import DocumentSession, handle_edit_proposal


@pytest.mark.asyncio
async def test_fuzzy_match_handles_whitespace_mismatch():
    """
    Verify that fuzzy matching handles trailing whitespace differences.
    """
    # The document has a trailing space on the empty line
    content_with_trailing_space = """Starting hyperparameter tuning.
    ray.init()
    \x20
    data_dir = os.path.abspath("./data")"""

    session = DocumentSession(content_with_trailing_space, set())

    # The agent proposes text WITHOUT the trailing space
    agent_proposal_before = """Starting hyperparameter tuning.
    ray.init()

    data_dir = os.path.abspath("./data")"""

    # This should now SUCCEED due to fuzzy matching
    result = await handle_edit_proposal(session, agent_proposal_before, "New content", "reason")
    assert "Edit applied successfully" in result or "User accepted" in result

    # Verify the content was updated
    assert session.current_content == "New content"


@pytest.mark.asyncio
async def test_fuzzy_match_strict_on_indentation():
    """
    Verify that fuzzy matching is STILL strict about leading indentation
    (to prevent matching the wrong code block).
    """
    content = """Starting hyperparameter tuning.
    ray.init()

    data_dir = os.path.abspath("./data")"""

    session = DocumentSession(content, set())

    # Agent uses 3 spaces instead of 4
    agent_proposal_before = """Starting hyperparameter tuning.
   ray.init()

   data_dir = os.path.abspath("./data")"""

    # This should still FAIL
    with pytest.raises(RuntimeError) as exc:
        await handle_edit_proposal(session, agent_proposal_before, "New content", "reason")

    assert "not found in document" in str(exc.value)
