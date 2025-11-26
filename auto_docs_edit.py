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
#   "pydantic>=2.0.0",
#   "langfuse>=2.0.0"
# ]
# ///
"""Iteratively apply Google style guide pages to a target markdown document.

Usage:
    uv run --script auto_docs_edit.py [--skip-through STYLE_FILE] <path-to-doc>

The script will iterate over every ``*.md`` file inside ``style/`` (each
scraped Google dev style-guide page). For each page it:

1. Sends the style-guide page and the current document to the LLM agent.
2. The agent applies edits serially using a tool.
3. Writes the updated document back to disk (if anything changed).
4. Pauses so you can review the result. Press <ENTER> to continue to the next guide or
   Ctrl+C to abort the run.
5. Records statistics and incident logs, then moves on to the next style page.

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
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from loguru import logger

from settings import (
    FINAL_PASS_MARKER,
    MODEL_NAME,
    STYLE_DIR,
)
from utils import (
    get_langfuse_handler,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Agent Tools & Session
# ---------------------------------------------------------------------------


class DocumentSession:
    """Manages the document state and edit history for the agent."""

    def __init__(self, content: str, seen_edits: set[tuple[str, str]]):
        self.initial_content = content
        self.current_content = content
        self.seen_edits = seen_edits  # Edits seen globally across all guides
        self.session_edits: list[tuple[str, str]] = []  # Edits applied in this session
        self.failed_edits: list[str] = []

    def apply_edit(self, before: str, after: str) -> str:
        """Tool implementation to replace text."""
        if before not in self.current_content:
            msg = f"Edit failed: Text '{before}' not found in document."
            self.failed_edits.append(msg)
            return msg

        # Check if this specific edit (before -> after) has been applied before (globally)
        # Note: logic could be refined. If text exists, maybe we SHOULD apply it even if seen before?
        # But original logic was to avoid loops.
        if (before, after) in self.seen_edits:
            # If it's already in the text, applying it again is a no-op if before==after,
            # but here before != after.
            # If 'before' exists, it means the previous application was reverted or 'before' appeared again.
            # We allow it, but log it?
            # Actually, let's allow the agent to decide.
            pass

        # Prevent infinite loops within the same session:
        # If we already applied this exact edit in this session, and 'before' is still there?
        # (e.g. multiple occurrences). We should apply it.
        # replace() replaces ALL occurrences by default?
        # Python's str.replace(old, new) replaces all occurrences.

        self.current_content = self.current_content.replace(before, after)
        self.session_edits.append((before, after))
        self.seen_edits.add((before, after))

        return "Edit applied successfully."


# ---------------------------------------------------------------------------
# Agent Logic
# ---------------------------------------------------------------------------


def process_style_guide(style_guide_text: str, session: DocumentSession) -> None:
    """Run the agent loop to apply edits from the style guide."""
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    @tool
    def apply_edit(before: str, after: str):
        """
        Replaces exact text in the document.
        Args:
            before: The exact text snippet to replace (must match character-for-character, including whitespace).
            after: The replacement text.
        """
        logger.info(f"Agent proposing edit: '{before}' -> '{after}'")
        return session.apply_edit(before, after)

    tools = [apply_edit]

    system_prompt = (
        "You are an expert technical editor. "
        "Given a STYLE GUIDE and a MARKDOWN DOCUMENT, apply the MINIMAL set of textual edits needed "
        "for the document to follow the guide. "
        "Use the `apply_edit` tool to apply changes. "
        "IMPORTANT: \n"
        "1. The 'before' text must match the document text *character-for-character*, including whitespace. "
        "2. If an edit fails (not found), the tool will return an error. You may try to correct the snippet or skip it. "
        "3. Do NOT apply purely stylistic rewrites unless mandated by the guide. "
        "4. Ensure code blocks remain syntactically valid. "
        "5. If no changes are needed, just stop. "
        "6. The `apply_edit` tool replaces ALL occurrences of the `before` text. "
        "If you only intend to replace one instance, ensure your `before` text is unique enough to identify it."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "Style Guide:\n{style_guide}\n\nDocument:\n{document}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=50)

    logger.info("Starting agent loop...")

    agent_executor.invoke(
        {
            "style_guide": style_guide_text,
            "document": session.current_content,
        },
        config={"callbacks": callbacks},
    )


# ---------------------------------------------------------------------------
# Vale Enforcement (LangChain Loop)
# ---------------------------------------------------------------------------


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

    # Maintain a memory of all (before, after) tuples ever suggested by the LLM
    seen_edits: set[tuple[str, str]] = set()

    # -------------------------------------------------------------------
    # Statistics counters
    # -------------------------------------------------------------------
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
            process_style_guide(style_text, session)
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

    # -------------------------------------------------------------------
    # Summary statistics
    # -------------------------------------------------------------------
    logger.info("=" * 80)
    logger.info("Edit summary statistics:")
    logger.info(f"Total edits applied successfully: {total_edits_applied}")
    logger.info("=" * 80)

    # -------------------------------------------------------------------
    # Vale Enforcement
    # -------------------------------------------------------------------
    logger.info("Starting Vale style enforcement...")
    enforce_vale_style(target_path)

    logger.info("All style pages and Vale checks processed. Done.")


if __name__ == "__main__":
    main()
