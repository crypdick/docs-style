import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from auto_docs_editor.notebook import NotebookHandler, is_notebook


def test_is_notebook(tmp_path):
    assert is_notebook(Path("foo.ipynb")) is True
    assert is_notebook(Path("foo.IPYNB")) is True
    assert is_notebook(Path("foo.md")) is False


def test_notebook_handler_init(tmp_path):
    nb = tmp_path / "test.ipynb"
    handler = NotebookHandler(nb)
    assert handler.notebook_path == nb
    assert handler.markdown_path == tmp_path / "test.md"


def test_is_paired_false_missing_md(tmp_path):
    nb = tmp_path / "test.ipynb"
    handler = NotebookHandler(nb)
    assert handler.is_paired() is False


def test_is_paired_true(tmp_path):
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    handler = NotebookHandler(nb)

    # Create md with jupytext metadata
    md.write_text(
        "---\njupytext:\n  text_representation:\n    extension: .md\n    format_name: myst\n    format_version: 0.13\n    jupytext_version: 1.14.0\n  kernelspec:\n    display_name: Python 3\n    language: python\n    name: python3\n---\n"
    )
    # Actually checking for "jupytext:" and "ipynb" in first 500 chars per implementation
    # Implementation: return "jupytext:" in content and "ipynb" in content
    # Wait, "ipynb" must be there.
    md.write_text("jupytext: ... ipynb ...")

    assert handler.is_paired() is True


def test_is_paired_false_no_metadata(tmp_path):
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    handler = NotebookHandler(nb)
    md.write_text("# Just a markdown file")

    assert handler.is_paired() is False


@patch("subprocess.run")
def test_ensure_paired_new(mock_run, tmp_path):
    """Test pairing when md doesn't exist."""
    nb = tmp_path / "test.ipynb"
    handler = NotebookHandler(nb)

    mock_run.return_value.returncode = 0

    result = handler.ensure_paired()

    assert result == handler.markdown_path
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "jupytext" in args
    assert "--set-formats" in args


def test_ensure_paired_existing_valid(tmp_path):
    """Test pairing when md exists and is valid."""
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    handler = NotebookHandler(nb)
    md.write_text("jupytext: ... ipynb ...")

    # Should not call subprocess
    with patch("subprocess.run") as mock_run:
        result = handler.ensure_paired()
        assert result == md
        mock_run.assert_not_called()


def test_ensure_paired_existing_invalid(tmp_path):
    """Test pairing when md exists but is not paired."""
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    handler = NotebookHandler(nb)
    md.write_text("# Not paired")

    with pytest.raises(RuntimeError) as exc:
        handler.ensure_paired()
    assert "Markdown file exists but is not paired" in str(exc.value)


@patch("subprocess.run")
def test_ensure_paired_failure(mock_run, tmp_path):
    """Test pairing failure."""
    nb = tmp_path / "test.ipynb"
    handler = NotebookHandler(nb)

    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error msg")

    with pytest.raises(RuntimeError) as exc:
        handler.ensure_paired()
    assert "Jupytext pairing failed" in str(exc.value)


@patch("subprocess.run")
def test_sync_back_success(mock_run, tmp_path):
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    md.touch()  # Needs to exist
    handler = NotebookHandler(nb)

    mock_run.return_value.returncode = 0

    handler.sync_back()

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "--sync" in args
    assert str(md) in args


def test_sync_back_no_file(tmp_path):
    nb = tmp_path / "test.ipynb"
    handler = NotebookHandler(nb)

    # Should not call subprocess, just return
    with patch("subprocess.run") as mock_run:
        handler.sync_back()
        mock_run.assert_not_called()


@patch("subprocess.run")
def test_sync_back_failure(mock_run, tmp_path):
    nb = tmp_path / "test.ipynb"
    md = tmp_path / "test.md"
    md.touch()
    handler = NotebookHandler(nb)

    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="sync error")

    with pytest.raises(RuntimeError) as exc:
        handler.sync_back()
    assert "Jupytext sync failed" in str(exc.value)
