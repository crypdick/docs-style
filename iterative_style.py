#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "openai>=1.16.0",
#   "whatthepatch>=1.0.0"
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

import os
import sys
from pathlib import Path
from typing import Optional, List, Tuple

from dotenv import load_dotenv
import openai
import itertools
import threading
import time
from contextlib import contextmanager
import re
import shutil
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "gpt-4.1-nano"  # Follow user instruction verbatim.
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
    "…PASTE UNCHANGED TEXT EXACTLY AS IT APPEARS (may span multiple lines)…\n"
    "</before>\n"
    "<after>\n"
    "…PASTE REPLACEMENT TEXT EXACTLY AS IT SHOULD APPEAR (may span multiple lines)…\n"
    "</after>\n"
    "</edit>\n\n"
    "The STYLE GUIDE will be supplied inside <style_guide>…</style_guide> and the DOCUMENT inside <document>…</document>. "
    "Only modify the DOCUMENT—never the STYLE GUIDE. "
    "Separate <edit> blocks only by whitespace/newlines—no other text. If several identical snippets require the same "
    "replacement, output ONE <edit> block for them. If the style guide does NOT apply, respond with exactly "
    f"'{DIFF_END_MARKER}'.  Do NOT output anything else. "
    "Never output an <edit> block whose <before> and <after> content are identical after normalising "
    "whitespace (including newlines, tabs, and spaces). If no such meaningful edits remain, respond with "
    f"'{DIFF_END_MARKER}'."
)

APPLY_SYSTEM_PROMPT = (
    "You are a diff application engine. You will receive the ORIGINAL "
    "markdown file, followed by a unified diff. Apply the diff faithfully and "
    "return ONLY the full updated markdown content. Do not output anything "
    "else."
)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_edits(edits_text: str) -> list[tuple[str, str]]:
    """Parse *edits_text* produced by the LLM into a list of ``(before, after)`` tuples.

    The function supports two formats:

    1. **XML blocks** (preferred, multi-line capable):::

           <edit>
           <before>
           [...any text...]
           </before>
           <after>
           [...any text...]
           </after>
           </edit>

    2. **Legacy single-line** ``<before> -> <after>`` entries.
    """

    # 1. Try the XML format first.
    xml_pattern = re.compile(
        r"<edit>\s*<before>(.*?)</before>\s*<after>(.*?)</after>\s*</edit>",
        re.DOTALL | re.IGNORECASE,
    )

    edits: list[tuple[str, str]] = []

    for match in xml_pattern.finditer(edits_text):
        before_raw, after_raw = match.group(1), match.group(2)
        before = before_raw.strip("\n")
        after = after_raw.strip("\n")
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

    # 2. Fallback to legacy single-line format.
    for raw in edits_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue  # Skip blank/comment lines.
        if "->" not in line:
            continue  # Malformed line.
        before, after = map(str.strip, line.split("->", 1))
        if not before or not after:
            continue

        if re.sub(r"\s+", "", before) == re.sub(r"\s+", "", after):
            continue  # whitespace-only change

        if before != after:
            edits.append((before, after))

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

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
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
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def generate_diff(style_guide: str, document: str) -> str:
    """Ask the LLM for a diff applying *style_guide* to *document*."""
    messages = [
        {"role": "system", "content": DIFF_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "<style_guide>\n" + style_guide + "\n</style_guide>\n\n" +
                "<document>\n" + document + "\n</document>"
            ),
        },
    ]
    return chat(messages)


def apply_diff(original_doc: str, edits_text: str) -> str:
    """Ask the LLM to apply *edits_text* to *original_doc* and return the new document."""

    messages = [
        {"role": "system", "content": APPLY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "ORIGINAL DOCUMENT:\n\n" + original_doc + "\n\n" +
                "EDITS (one per line, <before> -> <after>):\n\n" + edits_text
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

        # Show diff for manual review before automatic application.
        print("Generated diff:\n")
        print(diff)

        # Apply edits locally (deterministic and safer than LLM application).
        with spinner("Applying edits"):
            updated_doc, missed_snippets = _apply_edits_locally(doc_text, diff)

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
            print("Please review the changes and commit them in git if desired.\n"
                  "Press <ENTER> to continue to the next style guide, or Ctrl+C to abort.")
            try:
                input()
            except KeyboardInterrupt:
                print("\nAborted by user.")
                sys.exit(0)

    print("All style pages processed. Done.")


if __name__ == "__main__":
    main()
