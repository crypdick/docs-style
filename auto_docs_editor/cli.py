#!/usr/bin/env python3
"""Command-line interface for auto_docs_editor."""

from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

from auto_docs_editor.core import DocumentSession, process_style_guide
from auto_docs_editor.core_vale import enforce_vale_style
from auto_docs_editor.workflow import (
    get_style_guides,
    load_and_validate_target,
    setup_environment,
    sync_notebook_if_needed,
)
from settings import FINAL_PASS_MARKER
from utils import get_langfuse_handler, setup_logging


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Iteratively apply Google style guide pages to a markdown document or Jupyter notebook.",
    )
    parser.add_argument(
        "markdown_document",
        help="Path to the markdown document or Jupyter notebook (.ipynb) to process.",
    )
    parser.add_argument(
        "--skip-through",
        metavar="STYLE_FILE",
        help="Skip all style guide pages up to and including the specified filename.",
    )
    parser.add_argument(
        "--final-pass",
        action="store_true",
        help=(
            "Process only the subset of style-guide pages whose filenames are marked "
            f"with the '{FINAL_PASS_MARKER}' symbol. Use this as a quick final check "
            "after manual edits to catch rules that are easy to violate."
        ),
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enables YOLO MODE. Automatically accept and apply all edits.",
    )
    args = parser.parse_args()

    # Prepare logging (creates per-run directory and log file).
    log_file = setup_logging(tui_mode=False)
    logger.info(f"Logging configured. Full session log: {log_file}")

    # Setup environment and target
    setup_environment()
    context = load_and_validate_target(args.markdown_document)

    # Get style pages
    style_pages = get_style_guides(skip_through=args.skip_through, final_pass=args.final_pass)

    # Maintain a memory of all (before, after) tuples ever suggested by the LLM
    seen_edits: set[tuple[str, str]] = set()

    # Statistics counters
    total_edits_applied = 0

    # Get Langfuse handler for callbacks
    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    for idx, page_path in enumerate(style_pages, 1):
        # Re-read the document so that any manual edits the user made after the
        # previous iteration are taken into account.
        doc_text = context.target_path.read_text(encoding="utf-8")
        logger.info("=" * 80)
        logger.info(f"[{idx}/{len(style_pages)}] Processing style guide: {page_path.name}")
        style_text = page_path.read_text(encoding="utf-8")

        # Initialize Session
        session = DocumentSession(doc_text, seen_edits)

        try:
            asyncio.run(
                process_style_guide(style_text, session, callbacks=callbacks, review_callback=None)
            )
        except KeyboardInterrupt:
            logger.info("\n↷ Skip requested via Ctrl+C/ESC – moving to next style guide.\n")
            continue

        # Check results
        edits_made = len(session.session_edits)
        total_edits_applied += edits_made

        changed = session.current_content != session.initial_content

        if changed:
            context.target_path.write_text(session.current_content, encoding="utf-8")
            logger.success(f"-> Document updated via {page_path.name} ({edits_made} edits).")
        else:
            logger.info("-> No changes applied.\n")

        # Log stats for this page
        logger.info("Edit statistics for this style guide:")
        logger.info(f" • Edits applied         : {edits_made}")
        logger.info(f" • Edits failed          : {len(session.failed_edits)}")

        if session.failed_edits:
            logger.warning(f"Failed edits: {session.failed_edits}")

        # Only pause for user review if the document actually changed.
        if changed and not args.yolo:
            logger.info(
                "Please review the changes and commit them in git if desired.\n"
                "Press <ENTER> to continue to the next style guide, or Ctrl+C to abort."
            )
            try:
                input()
            except KeyboardInterrupt:
                logger.warning("\nAborted by user.")
                sys.exit(0)
        elif changed and args.yolo:
            logger.warning("YOLO mode enabled. Memento mori 💀")

    # Summary statistics
    logger.info("=" * 80)
    logger.info("Edit summary statistics:")
    logger.info(f"Total edits applied successfully: {total_edits_applied}")
    logger.info("=" * 80)

    # Vale Enforcement
    logger.info("Starting Vale style enforcement...")
    enforce_vale_style(context.target_path)

    # Sync back to notebook if needed
    sync_notebook_if_needed(context)

    logger.info("All style pages and Vale checks processed. Done.")


if __name__ == "__main__":
    main()
