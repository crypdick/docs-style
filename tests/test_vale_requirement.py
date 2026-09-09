"""Require Vale at entry points without calling external models or tools."""

import os
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

from docs_style import cli, tui
from settings import SKILL_DIR, VALE_CONFIG


@pytest.mark.parametrize("interface", [cli, tui])
def test_missing_vale_stops_editor_before_loading_target(interface, monkeypatch, tmp_path):
    document = tmp_path / "notebook.ipynb"
    document.write_text('{"cells": []}')
    monkeypatch.setattr(sys, "argv", ["docs-style", str(document)])
    entry_point = cli.main if interface is cli else tui.run

    with (
        patch("docs_style.core_vale.shutil.which", return_value=None),
        patch.object(interface, "setup_logging", return_value=tmp_path / "session.log"),
        patch.object(interface, "load_and_validate_target") as load_target,
        pytest.raises(RuntimeError, match="Vale is required"),
    ):
        entry_point()

    load_target.assert_not_called()
    assert document.read_text() == '{"cells": []}'


@pytest.fixture
def bash():
    executable = shutil.which("bash")
    if executable is None:
        pytest.skip("The skill's Bash wrapper requires Bash.")
    return executable


def test_wrapper_requires_vale(bash, tmp_path):
    result = subprocess.run(  # noqa: S603 - fixed wrapper and an isolated test PATH
        [bash, str(SKILL_DIR / "scripts" / "vale_check.sh"), str(tmp_path / "document.md")],
        env={**os.environ, "PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 127
    assert "Vale is required" in result.stderr


@pytest.mark.parametrize("status", [0, 1, 2])
def test_wrapper_preserves_findings_and_execution_status(bash, tmp_path, status):
    """Stub Vale to check the real wrapper's arguments and failure propagation."""
    document = tmp_path / "document with spaces.md"
    document.write_text("# Test\n")
    vale = tmp_path / "vale"
    vale.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"assert sys.argv[1:] == {[f'--config={VALE_CONFIG}', '--output=line', '--no-exit', str(document)]!r}\n"
        "print('document.md:1:1:Google.Headings:Style finding')\n"
        f"sys.exit({status})\n"
    )
    vale.chmod(0o755)
    result = subprocess.run(  # noqa: S603 - fixed wrapper and a generated test stub
        [bash, str(SKILL_DIR / "scripts" / "vale_check.sh"), str(document)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == status, result.stderr
    assert "Style finding" in result.stdout
