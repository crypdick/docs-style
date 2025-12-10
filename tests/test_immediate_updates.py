import pytest

from auto_docs_editor.core import DocumentSession


def test_immediate_file_updates(tmp_path):
    """Verify that the target file is updated immediately after each accepted edit."""
    # Setup initial file
    target_file = tmp_path / "test_doc.md"
    initial_content = "Line 1\nLine 2\nLine 3"
    target_file.write_text(initial_content, encoding="utf-8")

    # Callback to simulate TUI behavior (write to disk)
    def on_apply(new_content):
        target_file.write_text(new_content, encoding="utf-8")

    # Initialize session
    session = DocumentSession(initial_content, set(), on_apply=on_apply)

    # Edit 1: Change Line 1
    session.apply_edit("Line 1", "Header 1", "Make it a header")

    # Check immediate update
    current_content = target_file.read_text(encoding="utf-8")
    assert "Header 1" in current_content
    assert "Line 1" not in current_content
    assert current_content == "Header 1\nLine 2\nLine 3"

    # Edit 2: Change Line 3
    session.apply_edit("Line 3", "Footer", "Make it a footer")

    # Check immediate update again
    current_content = target_file.read_text(encoding="utf-8")
    assert "Footer" in current_content
    assert "Line 3" not in current_content
    assert current_content == "Header 1\nLine 2\nFooter"


def test_failed_save_propagates(tmp_path):
    """Verify that file save errors propagate (crash fast/loud)."""
    target_file = tmp_path / "protected.md"
    target_file.write_text("content", encoding="utf-8")

    def failing_on_apply(new_content):
        raise PermissionError("Disk full or something")

    session = DocumentSession("content", set(), on_apply=failing_on_apply)

    with pytest.raises(PermissionError, match="Disk full"):
        session.apply_edit("content", "new content", "reason")
