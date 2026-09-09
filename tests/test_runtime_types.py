"""Check runtime contracts without external services."""

from pathlib import Path

import pytest
from beartype.roar import BeartypeCallHintParamViolation

from docs_style.core import DocumentSession
from docs_style.notebook import NotebookHandler


def test_session_rejects_nontext_content():
    with pytest.raises(BeartypeCallHintParamViolation):
        DocumentSession(123, set())


def test_notebook_handler_requires_path():
    with pytest.raises(BeartypeCallHintParamViolation):
        NotebookHandler("document.ipynb")
    assert NotebookHandler(Path("document.ipynb")).markdown_path == Path("document.md")
