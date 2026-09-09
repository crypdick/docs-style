"""Core editing logic for docs_style."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from loguru import logger

from settings import MODEL_NAME
from utils import get_langfuse_handler


class LoguruCallbackHandler(BaseCallbackHandler):
    """Route agent logs through Loguru so they do not interfere with the TUI."""

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],  # noqa: ARG002 - LangChain callback signature
        *,
        run_id: UUID,  # noqa: ARG002 - LangChain callback signature
        parent_run_id: UUID | None = None,
        **kwargs: object,  # noqa: ARG002 - LangChain callback signature
    ) -> None:
        """Log when a chain starts."""
        # Only log top-level chain starts (no parent) to reduce noise
        if parent_run_id is None:
            chain_name = (serialized or {}).get("name", "Unknown")
            logger.debug(f"[Chain] Starting: {chain_name}")

    def on_chain_end(
        self,
        outputs: dict[str, Any],  # noqa: ARG002 - LangChain callback signature
        *,
        run_id: UUID,  # noqa: ARG002 - LangChain callback signature
        parent_run_id: UUID | None = None,
        **kwargs: object,  # noqa: ARG002 - LangChain callback signature
    ) -> None:
        """Log when a chain ends."""
        if parent_run_id is None:
            logger.debug("[Chain] Finished")

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,  # noqa: ARG002 - LangChain callback signature
        parent_run_id: UUID | None = None,  # noqa: ARG002 - LangChain callback signature
        **kwargs: object,  # noqa: ARG002 - LangChain callback signature
    ) -> None:
        """Log when a tool is invoked."""
        tool_name = serialized.get("name", "unknown_tool")
        # Truncate very long inputs for readability
        display_input = input_str[:500] + "..." if len(input_str) > 500 else input_str
        logger.debug(f"[Tool] Invoking: {tool_name}")
        logger.debug(f"[Tool] Input: {display_input}")

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,  # noqa: ARG002 - LangChain callback signature
        parent_run_id: UUID | None = None,  # noqa: ARG002 - LangChain callback signature
        **kwargs: object,  # noqa: ARG002 - LangChain callback signature
    ) -> None:
        """Log when a tool returns."""
        # Truncate very long outputs for readability
        display_output = output[:500] + "..." if len(output) > 500 else output
        logger.debug(f"[Tool] Output: {display_output}")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,  # noqa: ARG002 - LangChain callback signature
        parent_run_id: UUID | None = None,  # noqa: ARG002 - LangChain callback signature
        **kwargs: object,  # noqa: ARG002 - LangChain callback signature
    ) -> None:
        """Log tool errors."""
        logger.warning(f"[Tool] Error: {error}")


class DocumentSession:
    """Manages the document state and edit history for the agent."""

    def __init__(
        self,
        content: str,
        seen_edits: set[tuple[str, str]],
        on_apply: Callable[[str], Any] | None = None,
        content_provider: Callable[[], Any] | None = None,
    ) -> None:
        self.initial_content = content
        self.current_content = content
        self.seen_edits = seen_edits  # Edits seen globally across all guides
        self.session_edits: list[tuple[str, str]] = []  # Edits applied in this session
        self.failed_edits: list[str] = []
        self.current_style_guide: str = ""
        # Metrics for queryability
        self.stats = {"accepted": 0, "rejected": 0}
        self.on_apply = on_apply
        self.content_provider = content_provider

    def find_best_match(self, snippet: str) -> str | None:
        """Find the best match for the snippet in the document.

        Returns:
            The exact matching text from the document, or None if not found/ambiguous.
        """
        if snippet in self.current_content:
            return snippet

        fuzzy_matches = self._find_fuzzy_matches(snippet)
        if len(fuzzy_matches) == 1:
            return fuzzy_matches[0]

        return None

    async def apply_edit(self, before: str, after: str, reason: str = "") -> str:  # noqa: ARG002 - tool schema
        """Tool implementation to replace text."""
        # Refresh content from provider if available to catch out-of-band edits
        if self.content_provider:
            try:
                if inspect.iscoroutinefunction(self.content_provider):
                    self.current_content = await self.content_provider()
                else:
                    self.current_content = self.content_provider()
            except Exception as e:
                msg = f"Failed to refresh content from disk: {e}"
                logger.error(msg)
                raise RuntimeError(msg) from e

        best_match = self.find_best_match(before)
        if not best_match:
            # Fallback failed or ambiguous
            fuzzy_matches = self._find_fuzzy_matches(before)
            if len(fuzzy_matches) > 1:
                msg = f"Edit failed: Exact text not found, and fuzzy match is ambiguous ({len(fuzzy_matches)} matches found)."
            else:
                msg = "Edit failed: Text not found in document. Check for whitespace differences or try a smaller snippet."

            logger.error(msg)
            self.failed_edits.append(msg)
            raise RuntimeError(msg)

        # Use the actual matched text
        before = best_match

        self.current_content = self.current_content.replace(before, after)
        self.session_edits.append((before, after))
        self.seen_edits.add((before, after))

        if self.on_apply:
            if inspect.iscoroutinefunction(self.on_apply):
                await self.on_apply(self.current_content)
            else:
                self.on_apply(self.current_content)

        logger.info(f"Edit applied.\nBefore:\n```{before}```\nAfter->\n```{after}```")
        return "Edit applied successfully."

    def _find_fuzzy_matches(self, snippet: str) -> list[str]:
        """
        Find all occurrences of snippet in current_content, allowing for:
        1. Differences in trailing whitespace on lines.
        2. Differences in newline style (\r\n vs \n).
        """
        if not snippet:
            return []

        # Construct a regex that matches each line of the snippet
        # followed by optional whitespace and a newline

        snippet_lines = snippet.splitlines()
        regex_parts = []

        for line in snippet_lines:
            # Escape the line to treat it as literal text
            # rstrip() to ignore trailing whitespace in the snippet itself
            escaped_line = re.escape(line.rstrip())

            # Match the line, followed by optional horizontal whitespace
            part = escaped_line + r"[ \t]*"

            regex_parts.append(part)

        # Join lines with flexible newline matcher
        # We use \r?\n to match \n or \r\n
        pattern_str = r"\r?\n".join(regex_parts)

        try:
            pattern = re.compile(pattern_str)
            matches = list(pattern.finditer(self.current_content))
            return [m.group(0) for m in matches]
        except re.error as e:
            logger.warning(f"Failed to compile fuzzy regex: {e}")
            return []


CORE_INSTRUCTIONS = """

Apply the supplied style guide to the document with minimal, local edits.
Use `apply_edit` with the exact current text and a brief reason for each change.
The tool replaces every occurrence of `before`; include enough context to
identify a single occurrence when that is your intent.

Review the entire document, but apply edits sequentially: each tool call changes
the text that subsequent edits must match. If a match fails, correct the snippet
or skip it. Do not submit identical before and after text.

Preserve meaning, link destinations, anchors, and literal code. Edit code samples
only when the guide addresses their presentation and the change preserves syntax
and behavior. Avoid rephrasing clear prose beyond the supplied guide. Stop when
no useful corrections remain.
"""


def expand_edit_context(
    full_content: str, before: str, after: str, context_lines: int = 3
) -> tuple[str, str]:
    """Expand the edit context to include surrounding lines.

    Args:
        full_content: The full document text.
        before: The text being replaced.
        after: The replacement text.
        context_lines: Number of lines of context to include before and after.

    Returns:
        tuple[str, str]: The expanded (before, after) strings.
    """
    try:
        start_idx = full_content.index(before)
    except ValueError:
        # If text not found, return original strings (will fail later in apply_edit)
        return before, after

    end_idx = start_idx + len(before)

    # Find start of context (scan backwards)
    scan_start = start_idx

    # First, find the start of the line containing the match
    line_start = full_content.rfind("\n", 0, start_idx) + 1
    scan_start = line_start

    # Now go back N lines
    for _ in range(context_lines):
        if scan_start == 0:
            break
        prev_newline = full_content.rfind("\n", 0, scan_start - 1)
        if prev_newline == -1:
            scan_start = 0
            break
        scan_start = prev_newline + 1

    expanded_start = scan_start

    # Find end of context (scan forwards)
    scan_end = end_idx

    # Find the end of the line containing the match
    line_end = full_content.find("\n", end_idx)
    if line_end == -1:
        line_end = len(full_content)
    else:
        # Include the newline character of the current line
        line_end += 1

    scan_end = line_end

    # Now go forward N lines
    for _ in range(context_lines):
        next_newline = full_content.find("\n", scan_end)
        if next_newline == -1:
            scan_end = len(full_content)
            break
        # Include the newline
        scan_end = next_newline + 1

    expanded_end = scan_end

    # Extract the expanded original block
    original_block = full_content[expanded_start:expanded_end]

    # Construct the new block by splicing the replacement into the expanded block
    # We use relative offsets from expanded_start
    rel_start = start_idx - expanded_start
    rel_end = rel_start + len(before)

    new_block = original_block[:rel_start] + after + original_block[rel_end:]

    return original_block, new_block


async def handle_edit_proposal(
    session: DocumentSession,
    before: str,
    after: str,
    reason: str,
    review_callback: Callable[[str, str, str], Any] | None = None,
) -> str:
    """Handle the proposal of an edit, including interaction and application."""
    # First check if text exists (fail fast for agent)
    if before == after:
        logger.info(
            f"Agent proposed no-op edit.\nBefore:\n```{before}```\nAfter->\n```{after}```\n"
        )
        return "Edit failed: The 'before' and 'after' text are identical. No changes needed."

    best_match = session.find_best_match(before)
    if not best_match:
        msg = "Edit failed: Text not found in document. Check for whitespace differences or try a smaller snippet."
        logger.error(msg)
        raise RuntimeError(msg)

    if best_match != before:
        logger.info(
            f"Using fuzzy match for edit.\nOriginal: ```{before}```\nMatched: ```{best_match}```"
        )
        before = best_match

    if review_callback:
        # Interactive mode: Pause and ask user

        # Expand context for better visibility
        expanded_before, expanded_after = expand_edit_context(
            session.current_content, before, after
        )

        logger.info(
            f"Agent proposing edit for review.\nBefore:\n```{expanded_before}```\nAfter->\n```{expanded_after}```\n"
        )

        try:
            if inspect.iscoroutinefunction(review_callback):
                decision = await review_callback(expanded_before, expanded_after, reason)
            else:
                decision = review_callback(expanded_before, expanded_after, reason)
        except Exception as e:
            logger.error(f"Error in review callback: {e}")
            return f"Error interacting with user: {e}"

        if decision["status"] == "accepted":
            # User accepted -> Apply
            session.stats["accepted"] += 1
            # Apply the expanded edit to ensure context matches
            result = await session.apply_edit(expanded_before, expanded_after, reason)

            if "failed" in result.lower():
                err_msg = f"CRITICAL: User accepted edit but apply failed. Result: {result}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            return f"User accepted the proposal. {result}"
        if decision["status"] == "modified":
            # User modified -> Apply new text, count as rejected (quality issue)
            session.stats["rejected"] += 1
            new_text = decision.get("new_text", expanded_after)
            # Apply the expanded before with the user's new text
            result = await session.apply_edit(expanded_before, new_text, reason)

            if "failed" in result.lower():
                err_msg = f"CRITICAL: User modified edit but apply failed. Result: {result}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            return f"User changed suggested diff to:\n```{new_text}```\nResult: {result}"
        # User rejected -> Don't apply
        session.stats["rejected"] += 1
        rejection_reason = decision.get("reason", "No reason provided")
        logger.info(f"User rejected edit. Reason: {rejection_reason}")

        return f"User rejected the proposal. Reason given: {rejection_reason}. If the user provided feedback, incorporate that feedback and try again. If the user ignored your change, move on to the next proposed change. If you do not respond with a tool call, it will be assumed that you have no more edit proposals and the session will end."
    # Non-interactive mode: Apply immediately (no context expansion to stay faithful to agent request)
    logger.info(f"Agent proposing edit.\nBefore:\n```{before}```\nAfter->\n```{after}```\n")
    return await session.apply_edit(before, after, reason)


async def process_style_guide(
    style_guide_text: str,
    session: DocumentSession,
    callbacks: list[BaseCallbackHandler] | None = None,
    review_callback: Callable[[str, str, str], Any] | None = None,
    guide_name: str = "",
) -> None:
    """Run the agent loop to apply edits from the style guide.

    Args:
        style_guide_text: The style guide content
        session: DocumentSession to track edits
        callbacks: Optional list of callbacks (e.g., Langfuse)
        review_callback: Optional callback for interactive review.
                         Should accept (before, after, reason) and return dict with:
                         {"status": "accepted"|"rejected", "reason": str|None}
                         Can be async.
        guide_name: Optional name of the style guide file for tagging
    """
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    if callbacks is None:
        handler = get_langfuse_handler()
        callbacks = [handler] if handler else []
    else:
        callbacks = list(callbacks)

    # Store current style guide in session for downstream use (e.g. logging)
    session.current_style_guide = style_guide_text

    async def apply_edit(before: str, after: str, reason: str = "") -> str:
        """
        Replaces exact text in the document.
        Args:
            before: The exact text snippet to replace (must match character-for-character, including whitespace).
            after: The replacement text.
            reason: A brief explanation of why this edit is necessary based on the style guide.
        """
        return await handle_edit_proposal(session, before, after, reason, review_callback)

    tools = [tool(apply_edit)]

    # Refactored prompt structure: Style Guide as System, Document as User
    # Escape curly braces in style guide to prevent them being interpreted as variables
    safe_style_guide_text = style_guide_text.replace("{", "{{").replace("}", "}}")
    system_message = safe_style_guide_text + CORE_INSTRUCTIONS

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("user", "{document}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)

    # AgentExecutor writes verbose output directly to stdout, disrupting the TUI.
    callbacks.append(LoguruCallbackHandler())
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=50)

    logger.info(f"Processing {guide_name or 'style guide'}...")

    await agent_executor.ainvoke(
        {
            "document": session.current_content,
        },
        config={"callbacks": callbacks},
    )
