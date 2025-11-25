#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "openai>=1.16.0",
#   "loguru>=0.7.0",
#   "langchain>=0.1.0",
#   "langchain-openai>=0.0.5",
#   "pydantic>=2.0.0"
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
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field

from settings import (
    FINAL_PASS_MARKER,
    MODEL_NAME,
    STYLE_DIR,
)
from utils import (
    log_incident,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Console colours (ANSI)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pydantic Models for Structured Output
# ---------------------------------------------------------------------------


class StyleEdit(BaseModel):
    """A single edit to the document."""

    before: str = Field(
        ...,
        description="The exact text to be replaced, matching character-for-character including whitespace.",
    )
    after: str = Field(..., description="The replacement text.")
    reason: str | None = Field(
        None, description="A brief explanation of the style rule being applied."
    )


class StyleEditList(BaseModel):
    """A list of style edits."""

    edits: list[StyleEdit] = Field(..., description="List of edits to apply to the document.")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_edits(edits_output: StyleEditList | str) -> list[tuple[str, str]]:
    """Convert StyleEditList or legacy XML string into a list of (before, after) tuples."""
    if isinstance(edits_output, StyleEditList):
        return [
            (edit.before, edit.after) for edit in edits_output.edits if edit.before != edit.after
        ]
    return []


def _apply_edits_locally(original_doc: str, edits: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Apply edits to *original_doc*.

    Args:
        original_doc: The source text.
        edits: List of (before, after) tuples.
    """
    updated = original_doc
    missed: list[str] = []
    for before, after in edits:
        if before not in updated:
            missed.append(before)
            logger.warning(f"[warn] Skipping edit – snippet not found: {before!r}")
            continue
        updated = updated.replace(before, after)
    return updated, missed


# ---------------------------------------------------------------------------
# Diff generation
# ---------------------------------------------------------------------------


def generate_diff(style_guide: str, document: str) -> StyleEditList | None:
    """Request structured edits from the model."""
    logger.info("Generating diff via LLM...")
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)
    structured_llm = llm.with_structured_output(StyleEditList)

    system_prompt = (
        "You are an expert technical editor. "
        "Given a STYLE GUIDE and a MARKDOWN DOCUMENT, propose the MINIMAL set of textual edits needed "
        "for the document to follow the guide. "
        "IMPORTANT: The 'before' text must match the document text *character-for-character*, including whitespace. "
        "Do NOT pad 'before' or 'after' text with quotation marks. "
        "If the style guide does NOT apply or no changes are needed, return an empty list of edits. "
        "Avoid purely stylistic rewrites unless mandated by the guide. "
        "Ensure code blocks remain syntactically valid."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Style Guide:\n{style_guide}\n\nDocument:\n{document}"),
        ]
    )

    chain = prompt | structured_llm

    try:
        return chain.invoke({"style_guide": style_guide, "document": document})
    except KeyboardInterrupt:
        return None


# ---------------------------------------------------------------------------
# Vale Enforcement (LangChain Loop)
# ---------------------------------------------------------------------------


def enforce_vale_style(document_path: Path, max_retries: int = 5) -> None:
    """Iteratively run Vale and use an LLM to fix the errors."""
    if not shutil.which("vale"):
        logger.error("Vale is not installed or not in PATH. Skipping Vale enforcement.")
        return

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

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
            # JSON output is crashing in some environments, using line output as fallback
            result = subprocess.run(
                ["vale", "--output=line", str(document_path)],
                capture_output=True,
                text=True,
                check=False,  # Vale returns exit code 1 on errors
            )
        except Exception as e:
            logger.error(f"[Vale] Failed to run vale: {e}")
            return

        # Parse line output
        # Format: file:line:col:Check:Message
        # e.g. test.md:10:5:Google.We:Avoid using 'we'.
        output_lines = result.stdout.strip().splitlines()

        file_errors = []
        for line in output_lines:
            parts = line.split(":", 4)
            if len(parts) >= 5:
                # path = parts[0] # unused, we know it's the document
                line_num = parts[1]
                # col = parts[2] # unused
                check = parts[3]
                message = parts[4]
                file_errors.append(
                    {"Line": line_num, "Message": message.strip(), "Check": check, "Match": "N/A"}
                )  # Match is not available in line output easily

        if not file_errors:
            logger.success("[Vale] No errors found!")
            break

        # Filter/Format errors for the LLM
        error_list = []
        for err in file_errors:
            line = err.get("Line")
            msg = err.get("Message")
            rule = err.get("Check")
            # Match is N/A in line output, so we rely on line number and message
            error_list.append(f"- Line {line}: {msg} (Rule: {rule})")

        formatted_errors = "\n".join(error_list)
        logger.info(f"[Vale] Found {len(error_list)} errors:\n{formatted_errors}")

        current_text = document_path.read_text(encoding="utf-8")

        # Ask LLM to fix
        response = chain.invoke({"errors": formatted_errors, "document": current_text})

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

    # openai.api_key = os.environ["OPENAI_API_KEY"] # Not needed for LangChain

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
        if not diff.edits:  # diff is a StyleEditList object
            logger.info("-> Style guide not relevant or no changes detected. Skipping.\n")
            continue

        # Show raw diff from the model.
        logger.info("Generated diff (model output):\n")
        # Create a debug representation of the edits
        diff_debug = "\n".join(
            [
                f"<edit>\n<before>{e.before}</before>\n<after>{e.after}</after>\n<reason>{e.reason}</reason>\n</edit>"
                for e in diff.edits
            ]
        )
        logger.info(f"<yellow>{diff_debug}</>")

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

    # -------------------------------------------------------------------
    # Vale Enforcement
    # -------------------------------------------------------------------
    logger.info("Starting Vale style enforcement...")
    enforce_vale_style(target_path)

    logger.info("All style pages and Vale checks processed. Done.")


if __name__ == "__main__":
    main()
