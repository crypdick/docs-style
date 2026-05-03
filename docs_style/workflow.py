from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

from dotenv import load_dotenv
from loguru import logger

from auto_docs_editor.notebook import NotebookHandler, ensure_jupytext_installed, is_notebook
from settings import FINAL_PASS_MARKER, STYLE_DIR


class WorkflowContext(NamedTuple):
    target_path: Path
    original_target: Path
    notebook_handler: NotebookHandler | None


def setup_environment(require_api_key: bool = True) -> None:
    """Load environment variables and validate API keys."""
    load_dotenv()
    if require_api_key and not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is not set. Provide it in the environment or .env file.")
        sys.exit(1)


def load_and_validate_target(path_str: str) -> WorkflowContext:
    """Validate target file and handle Jupyter notebook pairing if needed."""
    target_path = Path(path_str).expanduser().resolve()
    if not target_path.is_file():
        logger.error(f"Error: {target_path} is not a file.")
        sys.exit(1)

    original_target = target_path
    notebook_handler = None

    if is_notebook(target_path):
        if not ensure_jupytext_installed():
            logger.error("Jupytext is not installed. Install it with: uv add jupytext")
            sys.exit(1)

        logger.info(f"Detected Jupyter notebook: {target_path}")
        notebook_handler = NotebookHandler(target_path)

        try:
            # Pair notebook with Markdown (will error if .md already exists)
            target_path = notebook_handler.ensure_paired()
            logger.info(f"Working with paired Markdown: {target_path}")
        except RuntimeError as e:
            logger.error(str(e))
            sys.exit(1)

    return WorkflowContext(
        target_path=target_path,
        original_target=original_target,
        notebook_handler=notebook_handler,
    )


def get_style_guides(skip_through: str | None = None, final_pass: bool = False) -> list[Path]:
    """Retrieve and filter the list of style guide files."""
    style_pages = sorted(STYLE_DIR.glob("*.md"), key=lambda p: p.name)

    if final_pass:
        logger.info("Processing final pass style rules only.")
        style_pages = [p for p in style_pages if p.stem.endswith(FINAL_PASS_MARKER)]

    if skip_through:
        skip_name = Path(skip_through).name
        try:
            skip_idx = next(i for i, p in enumerate(style_pages) if p.name == skip_name)
            style_pages = style_pages[skip_idx + 1 :]
            logger.info(f"Skipped {skip_idx} style pages.")
        except StopIteration:
            logger.error(f"--skip-through: '{skip_name}' not found among style pages.")
            sys.exit(1)

    if not style_pages:
        logger.info("No style guide pages left to process.")
        sys.exit(0)

    return style_pages


def sync_notebook_if_needed(context: WorkflowContext) -> None:
    """Sync changes back to the notebook if a handler is present."""
    if context.notebook_handler:
        logger.info("=" * 80)
        logger.info("Syncing changes back to notebook...")
        try:
            context.notebook_handler.sync_back()
            logger.success(f"Successfully updated notebook: {context.original_target}")
            logger.info(f"Paired Markdown preserved at: {context.target_path}")
        except RuntimeError as e:
            logger.error(f"Failed to sync back to notebook: {e}")
            logger.warning(f"Markdown edits are preserved in: {context.target_path}")
            sys.exit(1)
