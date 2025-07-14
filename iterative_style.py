#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "openai>=1.16.0"
# ]
# ///
"""Iteratively apply Google style guide pages to a target markdown document.

Usage:
    uv run --script iterative_style.py <path-to-doc>

The script will iterate over every ``*.md`` file inside ``style/`` (each
scraped Google dev style-guide page). For each page it:

1. Sends the style-guide page and the target document to the LLM and requests a
   unified diff that, when applied, transforms the target document so that it
   conforms to the style guide.  If the style page is not relevant, the LLM
   must return the literal string ``NO_CHANGES``.
2. Displays the diff to the user and asks whether to apply it.
3. If accepted, performs a second LLM call asking the model to apply the diff
   and output the new full document text.
4. Writes the updated document back to disk so that the user can review &
   commit the change.
5. Waits for the user to either continue to the next style page or abort.

Environment:
    OPENAI_API_KEY must be set and is preferably loaded from a ``.env`` file in
    the project root.
"""

from __future__ import annotations

import itertools
import os
import re
import shutil
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import openai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Console colours (ANSI)
# ---------------------------------------------------------------------------

RAW_DIFF_COLOR = "\033[33m"  # Yellow
FILTERED_DIFF_COLOR = "\033[32m"  # Green
RESET_COLOR = "\033[0m"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "o4-mini"  # "gpt-4.1-mini"
STYLE_DIR = Path(__file__).parent / "style"
INCIDENTS_DIR = Path(__file__).parent / "incidents"
DIFF_END_MARKER = "NO_CHANGES"

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

DIFF_SYSTEM_PROMPT = (
    "You are an expert technical editor. "
    "Given a STYLE GUIDE and a MARKDOWN DOCUMENT (each provided inside their own XML tags), propose the MINIMAL set of textual edits needed "
    "for the document to follow the guide. Output the edits in STRICT XML using the following template *repeated* "
    "once per edit (do not add attributes, comments, or any other markup):\n\n"
    "<edit>\n"
    "<before>\n"
    "…PASTE UNCHANGED TEXT EXACTLY AS IT APPEARS (may span multiple lines)\n"
    "</before>\n"
    "<after>\n"
    "…PASTE REPLACEMENT TEXT EXACTLY AS IT SHOULD APPEAR (may span multiple lines)\n"
    "</after>\n"
    "</edit>\n\n"
    "The STYLE GUIDE will be supplied inside <style_guide>…</style_guide> and the DOCUMENT inside <document>…</document>. "
    "Only modify the DOCUMENT—never the STYLE GUIDE. "
    "Do NOT remove or alter Markdown anchor tags or link identifiers such as '[](){ #anchor-id }' (and similar inline anchor syntaxes). "
    "Separate <edit> blocks only by whitespace/newlines—no other text. If several identical snippets require the same "
    "replacement, output ONE <edit> block for them. If the style guide does NOT apply, respond with exactly "
    f"'{DIFF_END_MARKER}'.  Do NOT output anything else. "
    "Never output an <edit> block whose <before> and <after> content are identical after normalising "
    "whitespace (including newlines, tabs, and spaces). These are a NO-OP and should be discarded. "
    "Each <edit> MUST remain small and local: the <before> snippet should not exceed 10 lines of text or ~300 characters. "
    "If the required change spans more than this limit, break it into multiple <edit> blocks, one per contiguous section. "
    "This is because if there are any mistake in the diff, it will fail to apply."
    " Preserve the existing wording, tone, and sentence structure unless the STYLE GUIDE explicitly requires a change or the text contains an unequivocal error (spelling, grammar, punctuation). "
    "Avoid making subjective rephrasings or stylistic rewrites not mandated by the STYLE GUIDE. "
    "Example 1: if the style guide is about correct usage of parenthesis, do not make edits that change usage of capitalization, punctuation, or other style rules."
    "Example 2: if the style guide is about tone, do not make edits that change how contractions are used."
    "Inside fenced (```\n...\n```) or indented code blocks, only make edits that are guaranteed to keep the code syntactically valid for its language. "
    "If applying a grammar or style rule could break, invalidate, or change the meaning of the code, skip that edit entirely. "
    "When several corrections are possible, prefer the one that achieves compliance with the least amount of change."
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_edits(edits_text: str) -> list[tuple[str, str]]:
    """Parse *edits_text* produced by the LLM into a list of ``(before, after)`` tuples.

    The function parses **XML blocks** of the form:

           <edit>
           <before>
           [...any text...]
           </before>
           <after>
           [...any text...]
           </after>
           </edit>

    """
    xml_pattern = re.compile(
        r"<edit>\s*<before>(.*?)</before>\s*<after>(.*?)</after>\s*</edit>",
        re.DOTALL | re.IGNORECASE,
    )

    edits: list[tuple[str, str]] = []

    for match in xml_pattern.finditer(edits_text):
        before_raw, after_raw = match.group(1), match.group(2)
        before = before_raw.strip("\n")
        after = after_raw.strip("\n")

        # Skip any edit that merely moves or modifies the sentinel value indicating
        # "no changes". The model occasionally (wrongly) embeds the sentinel
        # string inside an <edit> block which should be treated as a no-op.
        if before.strip() == DIFF_END_MARKER or after.strip() == DIFF_END_MARKER:
            continue  # Ignore this bogus edit outright.

        # Skip no-op edits: identical text or differences consisting only of whitespace.
        if not before or not after:
            continue

        if re.sub(r"\s+", "", before) == re.sub(r"\s+", "", after):
            # The change is purely whitespace – ignore it.
            continue

        if before != after:
            edits.append((before, after))

    if edits:
        return edits  # Successfully parsed XML edits.

    return edits


def _diff_has_changes(diff_text: str) -> bool:  # noqa: E302 – redefine with new semantics
    """Return ``True`` if *diff_text* has at least one **meaningful** edit.

    This version operates on the custom ``<before> -> <after>`` diff format
    rather than on unified diffs.
    """
    return bool(_parse_edits(diff_text))


def _apply_edits_locally(original_doc: str, edits_text: str) -> tuple[str, list[str]]:
    """Apply *edits_text* (``<before> -> <after>``) to *original_doc*.

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
            print(f"[warn] Skipping edit – snippet not found: {before!r}", file=sys.stderr)
            continue
        updated = updated.replace(before, after)
    return updated, missed


# ---------------------------------------------------------------------------
# Incident logging
# ---------------------------------------------------------------------------


def _clear_incidents_dir() -> None:
    """Remove all previous incident logs (fresh run)."""
    if INCIDENTS_DIR.exists():
        shutil.rmtree(INCIDENTS_DIR)
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)


def _log_incident(
    guide_path: Path,
    target_doc: Path,
    diff_text: str,
    missed_snippets: list[str],
) -> None:
    """Write an incident log file containing the problematic diff and context."""

    # Use timezone-aware datetime to avoid DeprecationWarning (Python 3.12+)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{timestamp}_{guide_path.stem}.log"
    incident_path = INCIDENTS_DIR / fname

    missed_section = "\n".join(f"- {s}" for s in missed_snippets) if missed_snippets else "<none>"

    content = (
        f"Guide: {guide_path.name}\n"
        f"Target doc: {target_doc}\n"
        f"Missed snippets: {missed_section}\n"
        f"--- DIFF START ---\n{diff_text}\n--- DIFF END ---\n"
    )

    incident_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# User-facing progress feedback
# ---------------------------------------------------------------------------


@contextmanager
def spinner(message: str = "Processing…"):
    """Display a simple spinner while the enclosed block is running."""
    stop_event = threading.Event()

    def _spin() -> None:
        for ch in itertools.cycle("|/-\\"):
            if stop_event.is_set():
                break
            sys.stdout.write(f"\r{message} {ch}")
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear the spinner line.
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
        sys.stdout.flush()

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop_event.set()
        t.join()


def chat(messages: list[dict[str, str]]) -> str:
    """Thin wrapper around the OpenAI chat completion API."""
    response = openai.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        # temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def generate_diff(style_guide: str, document: str) -> str:
    """Ask the LLM for a diff applying *style_guide* to *document*."""
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
    return chat(messages)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python iterative_style.py <path-to-markdown-document>")
        sys.exit(1)

    target_path = Path(sys.argv[1]).expanduser().resolve()
    if not target_path.is_file():
        print(f"Error: {target_path} is not a file.")
        sys.exit(1)

    # Load API key.
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set. Provide it in the environment or .env file.")
        sys.exit(1)

    openai.api_key = os.environ["OPENAI_API_KEY"]

    # Prepare incidents directory (fresh each run).
    _clear_incidents_dir()

    # Read the current state of the document once per iteration.
    doc_text = target_path.read_text(encoding="utf-8")

    style_pages = sorted(STYLE_DIR.glob("*.md"))
    if not style_pages:
        print(f"No style guide pages found in {STYLE_DIR}")
        sys.exit(1)

    for idx, page_path in enumerate(style_pages, 1):
        print("=" * 80)
        print(f"[{idx}/{len(style_pages)}] Processing style guide: {page_path.name}")
        style_text = page_path.read_text(encoding="utf-8")

        # Ask the LLM to create a diff while showing a spinner so that
        # the user knows the process is still ongoing.
        with spinner("Generating diff via LLM"):
            diff = generate_diff(style_text, doc_text)

        # Reject obviously malformed diffs up-front.
        if diff.strip() == DIFF_END_MARKER or not _diff_has_changes(diff):
            print("-> Style guide not relevant or no changes detected. Skipping.\n")
            continue

        # Show raw diff from the model.
        print("Generated diff (model output):\n")
        print(f"{RAW_DIFF_COLOR}{diff}{RESET_COLOR}")

        # Parse edits to identify the effective (non–no-op) changes.
        parsed_edits = _parse_edits(diff)
        if parsed_edits:
            filtered_diff_text = "\n\n".join(
                f"<edit>\n<before>\n{b}\n</before>\n<after>\n{a}\n</after>\n</edit>"
                for b, a in parsed_edits
            )
        else:
            filtered_diff_text = DIFF_END_MARKER

        if filtered_diff_text.strip() != diff.strip():
            print("\nDiff after filtering out no-op edits (will be applied):\n")
            print(f"{FILTERED_DIFF_COLOR}{filtered_diff_text}{RESET_COLOR}")

        # Apply edits locally (deterministic and safer than LLM application).
        with spinner("Applying edits"):
            updated_doc, missed_snippets = _apply_edits_locally(doc_text, filtered_diff_text)

        changed = updated_doc != doc_text

        if changed:
            # Only write back if something actually changed.
            target_path.write_text(updated_doc, encoding="utf-8")
            doc_text = updated_doc  # Use updated doc for subsequent iterations.
            print(f"-> Document updated via {page_path.name}.\n")
        else:
            print("-> Patch produced no net changes. Skipping write.\n")

        # Log incident if any edits were missed or nothing changed.
        if missed_snippets or not changed:
            _log_incident(page_path, target_path, diff, missed_snippets)

        # Only pause for user review if the document actually changed.
        if changed:
            print(
                "Please review the changes and commit them in git if desired.\n"
                "Press <ENTER> to continue to the next style guide, or Ctrl+C to abort."
            )
            try:
                input()
            except KeyboardInterrupt:
                print("\nAborted by user.")
                sys.exit(0)

    print("All style pages processed. Done.")


if __name__ == "__main__":
    main()
