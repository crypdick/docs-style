#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "openai>=1.16.0",
#   "loguru>=0.7.0"
# ]
# ///
"""Iteratively apply Google style guide pages to a target markdown document.

Usage:
    uv run --script auto_docs_edit.py [--skip-through STYLE_FILE] <path-to-doc>

The script will iterate over every ``*.md`` file inside ``style/`` (each
scraped Google dev style-guide page). For each page it:

1. Sends the style-guide page and the current document to the LLM and requests edits.
If the style page is not relevant, we skip the step and move on to the next style page.
2. Filters out duplicate, reversing, or
   no-op edits.
3. Applies the remaining edits locally via plain string replacement.
4. Writes the updated document back to disk (if anything changed).
5. Pauses so you can review the result. Press <ENTER> to continue to the next guide or
   Ctrl+C to abort the run.
6. Records statistics and incident logs, then moves on to the next style page.

Environment:
    OPENAI_API_KEY must be set and is preferably loaded from a ``.env`` file in
    the project root.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import openai
from dotenv import load_dotenv
from loguru import logger

from settings import (
    DIFF_END_MARKER,
    DIFF_SYSTEM_PROMPT,
    FINAL_PASS_MARKER,
    MODEL_NAME,
    STYLE_DIR,
)
from utils import (
    Spinner,
    check_cancellation,
    log_incident,
    restore_input_mode,
    run_with_spinner,
    setup_input_mode,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Console colours (ANSI)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_edits(edits_text: str) -> list[tuple[str, str]]:
    """Parse *edits_text* produced by the LLM into a list of ``(before, after)`` tuples.

    The function parses **XML blocks** of the form:

           <edit>
           <before>[...any text...]</before>
           <after>[...any text...]</after>
           <reason>[...any text...]</reason>
           </edit>

    """
    xml_pattern = re.compile(
        r"<edit>\s*<before>(.*?)</before>\s*<after>(.*?)</after>\s*(?:<reason>(.*?)</reason>)?\s*</edit>",
        re.DOTALL | re.IGNORECASE,
    )

    edits: list[tuple[str, str]] = []

    for match in xml_pattern.finditer(edits_text):
        before, after = match.group(1), match.group(2)

        # Skip any edit that merely moves or modifies the sentinel value indicating
        # "no changes". The model occasionally (wrongly) embeds the sentinel
        # string inside an <edit> block which should be treated as a no-op.
        if before.strip() == DIFF_END_MARKER or after.strip() == DIFF_END_MARKER:
            continue  # Ignore this bogus edit outright.

        if before != after:
            edits.append((before, after))

    if edits:
        return edits  # Successfully parsed XML edits.

    return edits


def _diff_has_changes(diff_text: str) -> bool:  # noqa: E302 – redefine with new semantics
    """Return True if *diff_text* contains at least one **meaningful** edit."""
    return bool(_parse_edits(diff_text))


def _apply_edits_locally(original_doc: str, edits_text: str) -> tuple[str, list[str]]:
    """Apply *edits_text* to *original_doc*.

    We perform **literal** (non-regex) replacements. All occurrences of each
    *before* snippet are replaced with the *after* snippet. If any *before*
    snippet is **not** found in the document, we leave the document unchanged
    and emit a warning to stderr.
    """
    updated = original_doc
    missed: list[str] = []
    for before, after in _parse_edits(edits_text):
        if before not in updated:
            missed.append(before)
            # Emit warning and continue.
            logger.warning(f"[warn] Skipping edit – snippet not found: {before!r}")
            continue
        updated = updated.replace(before, after)
    return updated, missed


# ---------------------------------------------------------------------------
# Diff generation (streaming with in-loop ESC cancellation)
# ---------------------------------------------------------------------------


def generate_diff(style_guide: str, document: str) -> str | None:
    """Request a streaming diff from the model with full ESC cancellation.

    The call proceeds in two phases:
    1. Waiting for the network request to reach the OpenAI servers and the
       first token to arrive (wrapped in ``run_with_spinner``).
    2. Streaming tokens; we print a tiny spinner and still honour ESC to abort
       mid-stream (only the tokens already generated are billed).
    """
    messages = [
        {"role": "system", "content": DIFF_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "<style_guide>\n"
                + style_guide
                + "\n</style_guide>\n\n"
                + "<document>\n"
                + document
                + "\n</document>"
            ),
        },
    ]

    def _start_stream():
        return openai.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,  # type: ignore
            stream=True,
        )

    stream = run_with_spinner(_start_stream, "Waiting for model response")
    if stream is None:
        return None  # User cancelled before the stream started.

    diff_chunks: list[str] = []
    fd, old_termios = setup_input_mode()
    spinner = Spinner("Generating diff via LLM")

    try:
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    diff_chunks.append(content)

            spinner.tick()

            if check_cancellation(fd):
                stream.close()
                return None

    finally:
        spinner.clear()
        restore_input_mode(fd, old_termios)

    return "".join(diff_chunks).strip()


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Iteratively apply Google style guide pages to a markdown document.",
    )
    parser.add_argument(
        "markdown_document",
        help="Path to the markdown document to process.",
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
    log_file = setup_logging()
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

    openai.api_key = os.environ["OPENAI_API_KEY"]

    # Maintain a memory of all (before, after) tuples ever suggested by the LLM
    # during this run. If the same exact edit appears again in a later round,
    # we silently ignore it to avoid redundant prompts and incident logs.
    seen_edits: set[tuple[str, str]] = set()
    # Track edits that actually made it into the document so that future
    # style-guide passes cannot revert them (avoiding tug-of-war between
    # conflicting guides).
    applied_edits: set[tuple[str, str]] = set()
    # -------------------------------------------------------------------
    # Statistics counters
    # -------------------------------------------------------------------
    total_edits_proposed = 0
    duplicates_dropped = 0
    reversals_dropped = 0
    edits_applied_successfully = 0
    edits_missed = 0

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
            # If the requested *skip-through* filename is not found, abort with an
            # explicit error rather than silently continuing. This prevents
            # accidental typos from going unnoticed and ensures the user
            # understands why the script did not behave as expected.
            logger.error(f"--skip-through: '{skip_name}' not found among style pages.")
            sys.exit(1)

    if not style_pages:
        logger.info("No style guide pages left to process.")
        sys.exit(0)

    for idx, page_path in enumerate(style_pages, 1):
        # Re-read the document so that any manual edits the user made after the
        # previous iteration are taken into account.
        doc_text = target_path.read_text(encoding="utf-8")
        logger.info("=" * 80)
        logger.info(f"[{idx}/{len(style_pages)}] Processing style guide: {page_path.name}")
        style_text = page_path.read_text(encoding="utf-8")

        # Ask the LLM to create a diff while showing a spinner so that
        # the user knows the process is still ongoing.
        diff = generate_diff(style_text, doc_text)

        # If *None* was returned, the user hit ESC during diff generation.
        if diff is None:
            logger.info("\n↷ Skip requested via ESC – moving to next style guide.\n")
            continue

        # Reject obviously malformed diffs up-front.
        if diff.strip() == DIFF_END_MARKER or not _diff_has_changes(diff):
            logger.info("-> Style guide not relevant or no changes detected. Skipping.\n")
            continue

        # Show raw diff from the model.
        logger.info("Generated diff (model output):\n")
        logger.info(f"<yellow>{diff}</>")

        # Parse edits to identify the effective (non–no-op) changes.
        parsed_edits = _parse_edits(diff)
        # Update stats – total edits proposed
        total_edits_proposed += len(parsed_edits)

        # -------------------------------------------------------------------
        # Step 1: drop edits we've already *seen* (same before→after pair).
        # -------------------------------------------------------------------
        unseen_edits: list[tuple[str, str]] = [
            (b, a) for (b, a) in parsed_edits if (b, a) not in seen_edits
        ]
        # Update stats – duplicates that were already seen
        duplicates_dropped += len(parsed_edits) - len(unseen_edits)

        # Record *all* parsed edits (including duplicates) so that any future
        # occurrences are recognised and skipped automatically.
        seen_edits.update(parsed_edits)

        # -------------------------------------------------------------------
        # Step 2: drop edits that would *undo* a change already applied.
        # That is, if we previously applied (x → y) and the current guide
        # proposes (y → x), we reject it.
        # -------------------------------------------------------------------
        non_reversing_edits: list[tuple[str, str]] = [
            (b, a) for (b, a) in unseen_edits if (a, b) not in applied_edits
        ]
        # Update stats – edits that would reverse previous changes
        reversals_dropped += len(unseen_edits) - len(non_reversing_edits)

        if not non_reversing_edits:
            logger.info(
                "-> All suggested edits are duplicates or would undo earlier edits. Skipping.\n"
            )
            continue

        # Rebuild the diff text using only the edits that are both unseen and non-reversing.
        filtered_diff_text = "\n\n".join(
            f"<edit>\n<before>{b}</before>\n<after>{a}</after>\n</edit>"
            for b, a in non_reversing_edits
        )

        if filtered_diff_text.strip() != diff.strip():
            logger.info("\nDiff after filtering out no-op edits (will be applied):\n")
            logger.info(f"<green>{filtered_diff_text}</>")

        # Apply edits locally (deterministic and safer than LLM application).
        updated_doc, missed_snippets = _apply_edits_locally(doc_text, filtered_diff_text)

        # Update stats – snippets that didn't match the document
        edits_missed += len(missed_snippets)

        changed = updated_doc != doc_text

        # Add successfully applied edits to the *applied_edits* memory so that
        # future passes can detect and avoid reversals. We exclude snippets
        # that were missed during application (i.e., not found in the doc).
        if changed:
            successful_edits = [
                (b, a) for (b, a) in non_reversing_edits if b not in missed_snippets
            ]
            applied_edits.update(successful_edits)
            # Update stats – successfully applied edits
            edits_applied_successfully += len(successful_edits)

        if changed:
            # Only write back if something actually changed.
            target_path.write_text(updated_doc, encoding="utf-8")
            logger.success(f"-> Document updated via {page_path.name}.\n")
        else:
            logger.info("-> Patch produced no net changes. Skipping write.\n")

        # -------------------------------------------------------------------
        # Per-style-guide statistics
        # -------------------------------------------------------------------
        page_total = len(parsed_edits)
        page_duplicates = len(parsed_edits) - len(unseen_edits)
        page_reversals = len(unseen_edits) - len(non_reversing_edits)
        page_applied = len(successful_edits) if changed else 0
        page_missed = len(missed_snippets)

        logger.info("Edit statistics for this style guide:")
        logger.info(f" • Proposed edits        : {page_total}")
        logger.info(f" • Duplicates skipped    : {page_duplicates}")
        logger.info(f" • Reversals dropped     : {page_reversals}")
        logger.info(f" • Edits applied         : {page_applied}")
        logger.info(f" • Edits missed/not found: {page_missed}\n")

        # Log incident if any edits were missed or nothing changed.
        if missed_snippets or not changed:
            log_incident(page_path, target_path, diff, missed_snippets)

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

    # -------------------------------------------------------------------
    # Summary statistics about edit processing
    # -------------------------------------------------------------------
    logger.info("=" * 80)
    logger.info("Edit summary statistics:")
    logger.info(f"Total edits proposed      : {total_edits_proposed}")
    logger.info(f" - Already seen (skipped) : {duplicates_dropped}")
    logger.info(f" - Reversals dropped      : {reversals_dropped}")
    logger.info(f"Edits applied successfully: {edits_applied_successfully}")
    logger.info(f"Edits missed (not found)  : {edits_missed}")
    logger.info("=" * 80)
    logger.info("All style pages processed. Done.")


if __name__ == "__main__":
    main()
