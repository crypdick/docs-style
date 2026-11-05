"""Check the version exposed by the installed editor package."""

import tomllib
from pathlib import Path

import docs_style


def test_package_version_matches_declared_project_version():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert docs_style.__version__ == project["project"]["version"]
