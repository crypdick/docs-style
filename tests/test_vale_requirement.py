"""Require Vale at entry points without calling external models or tools."""

import json
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


@pytest.fixture
def vale_wrapper(bash, tmp_path):
    vale = tmp_path / "vale"
    vale.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "print(json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd()}))\n"
        "print('document.md:1:1:Google.Headings:Style finding')\n"
        "sys.exit(int(os.environ['VALE_STUB_STATUS']))\n"
    )
    vale.chmod(0o755)

    def run(document, *, cwd, status=0):
        return subprocess.run(  # noqa: S603 - fixed wrapper and a generated test stub
            [bash, str(SKILL_DIR / "scripts" / "vale_check.sh"), str(document)],
            cwd=cwd,
            env={
                **os.environ,
                "PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}",
                "VALE_STUB_STATUS": str(status),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    return run


@pytest.mark.parametrize("status", [0, 1, 2])
def test_wrapper_preserves_findings_and_execution_status(vale_wrapper, tmp_path, status):
    document = tmp_path / "document with spaces.md"
    document.write_text("# Test\n")
    result = vale_wrapper(document, cwd=tmp_path, status=status)
    assert result.returncode == status, result.stderr
    assert "Style finding" in result.stdout
    assert json.loads(result.stdout.splitlines()[0])["args"] == [
        f"--config={VALE_CONFIG}",
        "--no-global",
        "--output=line",
        "--no-exit",
        str(document),
    ]


@pytest.mark.parametrize("relative_document", [False, True])
@pytest.mark.parametrize("nested_config", [False, True])
def test_wrapper_uses_nearest_document_config(
    vale_wrapper, tmp_path, relative_document, nested_config
):
    project = tmp_path / "project with spaces"
    document_dir = project / "docs" / "nested"
    document_dir.mkdir(parents=True)
    (project / ".vale.ini").write_text("[*]\nBasedOnStyles = Vale\n")
    config_dir = project / "docs" if nested_config else project
    config = config_dir / ".vale.ini"
    config.write_text("[*]\nBasedOnStyles = Vale\n")
    document = document_dir / "document with spaces.md"
    document.write_text("# Test\n")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / ".vale.ini").write_text("This config must not be used.\n")
    target = os.path.relpath(document, unrelated) if relative_document else document

    result = vale_wrapper(target, cwd=unrelated)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[0]) == {
        "args": [
            f"--config={config}",
            "--no-global",
            "--output=line",
            "--no-exit",
            document.relative_to(config_dir).as_posix(),
        ],
        "cwd": str(config_dir),
    }


@pytest.mark.parametrize("status", [0, 1, 2])
def test_wrapper_uses_config_relative_readme_scope(vale_wrapper, tmp_path, status):
    project = tmp_path / "project"
    project.mkdir()
    config = project / ".vale.ini"
    config.write_text("[README.md]\nGoogle.Headings = NO\n")
    document = project / "README.md"
    document.write_text("# Test\n")

    result = vale_wrapper(document, cwd=tmp_path, status=status)

    assert result.returncode == status, result.stderr
    invocation = json.loads(result.stdout.splitlines()[0])
    assert invocation["args"][0] == f"--config={config}"
    assert invocation["args"][-1] == "README.md"
    assert invocation["cwd"] == str(project)


def test_wrapper_fallback_ignores_working_directory_config(vale_wrapper, tmp_path):
    document = tmp_path / "document.md"
    document.write_text("# Test\n")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / ".vale.ini").write_text("This config must not be used.\n")

    result = vale_wrapper("../document.md", cwd=unrelated)

    assert result.returncode == 0, result.stderr
    invocation = json.loads(result.stdout.splitlines()[0])
    assert invocation["args"][0] == f"--config={VALE_CONFIG}"
    assert "--no-global" in invocation["args"]
    assert invocation["args"][-1] == str(document)
