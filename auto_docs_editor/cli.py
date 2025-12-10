#!/usr/bin/env python3
"""Command-line interface for auto_docs_editor."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger

from auto_docs_editor.core import DocumentSession, process_style_guide
from auto_docs_editor.notebook import NotebookHandler, ensure_jupytext_installed, is_notebook
from settings import FINAL_PASS_MARKER, MODEL_NAME, STYLE_DIR
from utils import get_langfuse_handler, setup_logging


def enforce_vale_style(document_path: Path, max_retries: int = 5) -> None:
    """Iteratively run Vale and use an LLM to fix the errors."""
    if not shutil.which("vale"):
        logger.error("Vale is not installed or not in PATH. Skipping Vale enforcement.")
        return

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    prompt_template = ChatPromptTemplate.from_template(
        "You are a technical editor. I will provide you with a markdown document and a list of style errors found by Vale (Google Style Guide).\n"
        "Your task is to fix the style errors in the document. \n"
        "If a Vale error is too pedantic, false positive, or makes the text worse/awkward, you may ignore it.\n"
        "If you determine that ALL remaining errors are pedantic or should be ignored, strictly output the single word: PEDANTIC\n"
        "Otherwise, output the FULL corrected markdown document. Do not include any markdown fences (like ```markdown) or conversational text.\n\n"
        "Errors:\n{errors}\n\n"
        "Document:\n{document}"
    )
    chain = prompt_template | llm | StrOutputParser()

    for attempt in range(1, max_retries + 1):
        logger.info(f"[Vale] Enforcement attempt {attempt}/{max_retries}...")

        # Run Vale
        try:
            result = subprocess.run(
                ["vale", "--output=line", str(document_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as e:
            logger.error(f"[Vale] Failed to run vale: {e}")
            return

        # Parse line output
        output_lines = result.stdout.strip().splitlines()

        file_errors = []
        for line in output_lines:
            parts = line.split(":", 4)
            if len(parts) >= 5:
                line_num = parts[1]
                check = parts[3]
                message = parts[4]
                file_errors.append(
                    {"Line": line_num, "Message": message.strip(), "Check": check, "Match": "N/A"}
                )

        if not file_errors:
            logger.success("[Vale] No errors found!")
            break

        # Filter/Format errors for the LLM
        error_list = []
        for err in file_errors:
            line = err.get("Line")
            msg = err.get("Message")
            rule = err.get("Check")
            error_list.append(f"- Line {line}: {msg} (Rule: {rule})")

        formatted_errors = "\n".join(error_list)
        logger.info(f"[Vale] Found {len(error_list)} errors:\n{formatted_errors}")

        current_text = document_path.read_text(encoding="utf-8")

        # Ask LLM to fix
        response = chain.invoke(
            {"errors": formatted_errors, "document": current_text}, config={"callbacks": callbacks}
        )

        if response.strip() == "PEDANTIC":
            logger.info("[Vale] LLM determined remaining errors are pedantic. Stopping.")
            break

        # Heuristic check: if response is drastically shorter, something might be wrong
        if len(response) < len(current_text) * 0.5:
            logger.warning(
                "[Vale] LLM response seems too short. Aborting this step to prevent data loss."
            )
            break

        # Apply changes
        if response != current_text:
            document_path.write_text(response, encoding="utf-8")
            logger.success("[Vale] Applied fixes from LLM.")
        else:
            logger.info("[Vale] LLM proposed no changes. Stopping.")
            break
    else:
        logger.warning("[Vale] Max retries reached. Some errors may remain.")


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

    target_path = Path(args.markdown_document).expanduser().resolve()
    if not target_path.is_file():
        logger.error(f"Error: {target_path} is not a file.")
        sys.exit(1)

    # Load API key.
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is not set. Provide it in the environment or .env file.")
        sys.exit(1)

    # Handle Jupyter notebooks
    notebook_handler = None
    original_target = target_path

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

    # Maintain a memory of all (before, after) tuples ever suggested by the LLM
    seen_edits: set[tuple[str, str]] = set()

    # Statistics counters
    total_edits_applied = 0

    # Always process style pages in a deterministic order (alphabetical by filename).
    style_pages = sorted(STYLE_DIR.glob("*.md"), key=lambda p: p.name)

    # If --final-pass is active, restrict to pages whose stem ends with the marker.
    if args.final_pass:
        logger.info("Processing final pass style rules only.")
        style_pages = [p for p in style_pages if p.stem.endswith(FINAL_PASS_MARKER)]

    # Optionally skip pages up to and including the requested filename.
    if args.skip_through:
        skip_name = Path(args.skip_through).name
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

    # Get Langfuse handler for callbacks
    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    for idx, page_path in enumerate(style_pages, 1):
        # Re-read the document so that any manual edits the user made after the
        # previous iteration are taken into account.
        doc_text = target_path.read_text(encoding="utf-8")
        logger.info("=" * 80)
        logger.info(f"[{idx}/{len(style_pages)}] Processing style guide: {page_path.name}")
        style_text = page_path.read_text(encoding="utf-8")

        # Initialize Session
        session = DocumentSession(doc_text, seen_edits)

        try:
            process_style_guide(style_text, session, callbacks=callbacks, interactive=False)
        except KeyboardInterrupt:
            logger.info("\n↷ Skip requested via Ctrl+C/ESC – moving to next style guide.\n")
            continue

        # Check results
        edits_made = len(session.session_edits)
        total_edits_applied += edits_made

        changed = session.current_content != session.initial_content

        if changed:
            target_path.write_text(session.current_content, encoding="utf-8")
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
    enforce_vale_style(target_path)

    # Sync back to notebook if needed
    if notebook_handler:
        logger.info("=" * 80)
        logger.info("Syncing changes back to notebook...")
        try:
            notebook_handler.sync_back()
            logger.success(f"Successfully updated notebook: {original_target}")
            logger.info(f"Paired Markdown preserved at: {target_path}")
        except RuntimeError as e:
            logger.error(f"Failed to sync back to notebook: {e}")
            logger.warning(f"Markdown edits are preserved in: {target_path}")
            sys.exit(1)

    logger.info("All style pages and Vale checks processed. Done.")


if __name__ == "__main__":
    main()
