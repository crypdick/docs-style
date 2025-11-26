"""Jupyter notebook support via Jupytext."""

from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger


class NotebookHandler:
    """Handle conversion between .ipynb and Markdown via Jupytext.

    Requires notebooks to be paired with Markdown files using:
        jupytext --set-formats ipynb,md:myst notebook.ipynb
    """

    def __init__(self, notebook_path: Path):
        """Initialize handler for a notebook file.

        Args:
            notebook_path: Path to the .ipynb file
        """
        self.notebook_path = notebook_path
        self.markdown_path = notebook_path.with_suffix(".md")

    def ensure_paired(self) -> Path:
        """Ensure the notebook is paired with a Markdown file.

        Returns:
            Path to the paired Markdown file

        Raises:
            RuntimeError: If the Markdown file already exists or pairing fails
        """
        # Check if markdown already exists
        if self.markdown_path.exists():
            raise RuntimeError(
                f"Markdown file already exists: {self.markdown_path}\n"
                f"Please delete it or use a different notebook.\n"
                f"The tool will create a paired Markdown file automatically."
            )

        logger.info(f"Pairing notebook with Markdown: {self.notebook_path}")

        try:
            # Pair the notebook with MyST Markdown format
            _result = subprocess.run(
                [
                    "jupytext",
                    "--set-formats",
                    "ipynb,md:myst",
                    str(self.notebook_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.success(f"Created paired Markdown: {self.markdown_path}")
            return self.markdown_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pair notebook: {e.stderr}")
            raise RuntimeError(f"Jupytext pairing failed: {e.stderr}") from e

    def sync_back(self) -> None:
        """Sync the edited Markdown back to the notebook using jupytext --sync."""
        if not self.markdown_path.exists():
            logger.warning("No Markdown file to sync back")
            return

        logger.info(f"Syncing Markdown changes back to notebook: {self.notebook_path}")

        try:
            _result = subprocess.run(
                ["jupytext", "--sync", str(self.markdown_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.success("Synced Markdown to notebook")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to sync back to notebook: {e.stderr}")
            raise RuntimeError(f"Jupytext sync failed: {e.stderr}") from e


def is_notebook(path: Path) -> bool:
    """Check if a path is a Jupyter notebook.

    Args:
        path: Path to check

    Returns:
        True if the path is a .ipynb file
    """
    return path.suffix.lower() == ".ipynb"


def ensure_jupytext_installed() -> bool:
    """Check if jupytext is installed.

    Returns:
        True if jupytext is available, False otherwise
    """
    try:
        _result = subprocess.run(
            ["jupytext", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return _result.returncode == 0
    except FileNotFoundError:
        return False
