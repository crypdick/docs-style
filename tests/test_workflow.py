from unittest.mock import Mock, patch

import pytest

from auto_docs_editor.workflow import (
    WorkflowContext,
    get_style_guides,
    load_and_validate_target,
    setup_environment,
)


def test_setup_environment_success(monkeypatch):
    """Test environment setup when API key is present."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # Should not raise
    setup_environment(require_api_key=True)


@patch("auto_docs_editor.workflow.load_dotenv")
def test_setup_environment_failure(mock_load_dotenv, monkeypatch):
    """Test environment setup failure when API key is missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc:
        setup_environment(require_api_key=True)
    assert exc.value.code == 1


def test_setup_environment_not_required(monkeypatch):
    """Test environment setup when API key is not required."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Should not raise
    setup_environment(require_api_key=False)


def test_load_and_validate_target_markdown(tmp_path):
    """Test validating a standard markdown file."""
    f = tmp_path / "test.md"
    f.touch()

    context = load_and_validate_target(str(f))
    assert isinstance(context, WorkflowContext)
    assert context.target_path == f
    assert context.original_target == f
    assert context.notebook_handler is None


def test_load_and_validate_target_missing(tmp_path):
    """Test validating a non-existent file."""
    f = tmp_path / "nonexistent.md"

    with pytest.raises(SystemExit) as exc:
        load_and_validate_target(str(f))
    assert exc.value.code == 1


@patch("auto_docs_editor.workflow.ensure_jupytext_installed")
@patch("auto_docs_editor.workflow.NotebookHandler")
def test_load_and_validate_target_notebook(mock_handler_cls, mock_ensure_jupytext, tmp_path):
    """Test validating a notebook file."""
    nb_path = tmp_path / "test.ipynb"
    nb_path.touch()
    md_path = tmp_path / "test.md"

    mock_ensure_jupytext.return_value = True

    # Setup mock handler instance
    mock_handler = Mock()
    mock_handler.ensure_paired.return_value = md_path
    mock_handler_cls.return_value = mock_handler

    context = load_and_validate_target(str(nb_path))

    assert context.original_target == nb_path
    assert context.target_path == md_path
    assert context.notebook_handler == mock_handler
    mock_handler.ensure_paired.assert_called_once()


@patch("auto_docs_editor.workflow.ensure_jupytext_installed")
def test_load_and_validate_target_notebook_no_jupytext(mock_ensure_jupytext, tmp_path):
    """Test validating a notebook without jupytext installed."""
    nb_path = tmp_path / "test.ipynb"
    nb_path.touch()

    mock_ensure_jupytext.return_value = False

    with pytest.raises(SystemExit) as exc:
        load_and_validate_target(str(nb_path))
    assert exc.value.code == 1


@patch("auto_docs_editor.workflow.STYLE_DIR")
def test_get_style_guides_basic(mock_style_dir, tmp_path):
    """Test retrieving style guides."""
    # Create fake style files
    p1 = tmp_path / "01-a.md"
    p2 = tmp_path / "02-b.md"
    mock_style_dir.glob.return_value = [p1, p2]

    guides = get_style_guides()
    assert len(guides) == 2
    assert guides == [p1, p2]


@patch("auto_docs_editor.workflow.STYLE_DIR")
@patch("auto_docs_editor.workflow.FINAL_PASS_MARKER", "+")
def test_get_style_guides_final_pass(mock_style_dir, tmp_path):
    """Test filtering for final pass."""
    p1 = tmp_path / "01-regular.md"
    p2 = tmp_path / "02-final+.md"
    mock_style_dir.glob.return_value = [p1, p2]

    guides = get_style_guides(final_pass=True)
    assert len(guides) == 1
    assert guides == [p2]


@patch("auto_docs_editor.workflow.STYLE_DIR")
def test_get_style_guides_skip_through(mock_style_dir, tmp_path):
    """Test skipping through specific guides."""
    p1 = tmp_path / "01-a.md"
    p2 = tmp_path / "02-b.md"
    p3 = tmp_path / "03-c.md"
    mock_style_dir.glob.return_value = [p1, p2, p3]

    # Skip through 02-b.md, should return [p3]
    guides = get_style_guides(skip_through="02-b.md")
    assert len(guides) == 1
    assert guides == [p3]


@patch("auto_docs_editor.workflow.STYLE_DIR")
def test_get_style_guides_skip_not_found(mock_style_dir, tmp_path):
    """Test skipping a guide that doesn't exist."""
    p1 = tmp_path / "01-a.md"
    mock_style_dir.glob.return_value = [p1]

    with pytest.raises(SystemExit) as exc:
        get_style_guides(skip_through="nonexistent.md")
    assert exc.value.code == 1


@patch("auto_docs_editor.workflow.STYLE_DIR")
def test_get_style_guides_empty(mock_style_dir):
    """Test behavior when no guides are found."""
    mock_style_dir.glob.return_value = []

    with pytest.raises(SystemExit) as exc:
        get_style_guides()
    assert exc.value.code == 0
