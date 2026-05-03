"""Tests for handling content that contains backticks (code fences)."""

import pytest

from docs_style.core import DocumentSession


class TestBackticksInContent:
    """Tests for handling content that contains backticks."""

    def test_document_session_handles_backticks_in_text(self):
        """Test that DocumentSession can find and replace text containing backticks."""
        content = """# Example

Here is some code:

```python
def hello():
    print("Hello")
```

More text here.
"""
        session = DocumentSession(content, set())

        # The text with backticks should be findable
        code_block = """```python
def hello():
    print("Hello")
```"""

        match = session.find_best_match(code_block)
        assert match is not None, "Should find text containing backticks"
        assert match == code_block

    @pytest.mark.asyncio
    async def test_document_session_replaces_text_with_backticks(self):
        """Test that DocumentSession can replace text containing backticks."""
        content = """# Example

```python
def old():
    pass
```
"""
        session = DocumentSession(content, set())

        before = """```python
def old():
    pass
```"""
        after = """```python
def new():
    pass
```"""

        # This should not raise an error
        result = await session.apply_edit(before, after)

        assert "successfully" in result.lower()
        assert "def new():" in session.current_content
        assert "def old():" not in session.current_content

    @pytest.mark.asyncio
    async def test_error_message_does_not_corrupt_backticks(self):
        """Test that error messages properly handle text with backticks.

        This ensures that when text containing backticks is not found,
        the error message doesn't get corrupted or cause parsing issues.
        """
        content = "Simple content without the code block"
        session = DocumentSession(content, set())

        # Try to find text that contains backticks but isn't in the document
        code_block = """```python
def missing():
    pass
```"""

        match = session.find_best_match(code_block)
        assert match is None, "Should not find text that doesn't exist"

        # Attempting to apply should raise RuntimeError with a clear message
        with pytest.raises(RuntimeError) as exc_info:
            await session.apply_edit(code_block, "replacement")

        # The error message should be present and not corrupted
        assert "not found" in str(exc_info.value).lower()
