from unittest.mock import Mock, patch

import pytest

from bulk_pr_autodocs import process_document, repo_full_name_from_remote_url
from settings import ROOT_DIR


@pytest.mark.parametrize(
    "url",
    ["git@github.com:owner/widget.git", "https://github.com/owner/widget.git"],
)
def test_remote_name_preserves_trailing_git_characters(url):
    assert repo_full_name_from_remote_url(url) == "owner/widget"


def test_bulk_uses_current_editor_entrypoint(tmp_path):
    document = tmp_path / "guide.md"
    document.write_text("# Guide\n", encoding="utf-8")
    github_client = Mock()

    # An unchanged document stops before any GitHub operation.
    with patch("bulk_pr_autodocs.run", return_value="") as run:
        process_document(tmp_path, "guide.md", "main", "origin", github_client, False)

    editor_calls = [call.args[0] for call in run.call_args_list if call.args[0][0] == "uv"]
    command = ["uv", "run", "--project", str(ROOT_DIR), "docs-style-edit"]
    assert editor_calls == [
        [*command, "--yolo", str(document)],
        [*command, "--final-pass", "--yolo", str(document)],
    ]
    assert not github_client.mock_calls
