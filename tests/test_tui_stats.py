from unittest.mock import patch

import pytest
from textual.widgets import Label

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.tui import AutoDocsEditorTUI


@pytest.mark.asyncio
async def test_update_stats_label(tmp_path):
    """Test that the stats label updates correctly."""
    doc_path = tmp_path / "test.md"
    doc_path.write_text("content")
    style_path = tmp_path / "style.md"

    controller = ReviewController(
        document_path=doc_path,
        style_pages=[style_path],
        seen_edits=set(),
    )

    # Mock get_langfuse_handler to prevent import errors or side effects
    with patch("auto_docs_editor.tui.get_langfuse_handler", return_value=None):
        app = AutoDocsEditorTUI(controller)

        async with app.run_test() as pilot:
            # Initial state
            label = app.query_one("#progress-label", Label)

            # Modify controller stats manually
            controller.total_accepted = 5
            controller.total_rejected = 3

            # Call update method
            app.update_stats_label()

            # Check update
            label = app.query_one("#progress-label", Label)
            text_content = str(label.render())

            assert "Accepted: 5" in text_content
            assert "Rejected: 3" in text_content
