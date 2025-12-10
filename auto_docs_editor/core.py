"""Core editing logic for auto_docs_editor."""

from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from typing import Any

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    # Fallback for newer langchain versions (1.1.0+)
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from loguru import logger

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
except ImportError:
    Langfuse = None
    LangfuseCallbackHandler = None

from settings import MODEL_NAME


class DocumentSession:
    """Manages the document state and edit history for the agent."""

    def __init__(
        self,
        content: str,
        seen_edits: set[tuple[str, str]],
        on_apply: Callable[[str], Any] | None = None,
        content_provider: Callable[[], Any] | None = None,
    ):
        self.initial_content = content
        self.current_content = content
        self.seen_edits = seen_edits  # Edits seen globally across all guides
        self.session_edits: list[tuple[str, str]] = []  # Edits applied in this session
        self.failed_edits: list[str] = []
        self.trace_id: str | None = None
        self.current_style_guide: str = ""
        # Metrics for queryability
        self.stats = {"accepted": 0, "rejected": 0}
        self.on_apply = on_apply
        self.content_provider = content_provider

    async def apply_edit(self, before: str, after: str, reason: str = "") -> str:
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

        if before not in self.current_content:
            msg = f"Edit failed: Text ```{before}``` not found in document."
            logger.error(msg)
            self.failed_edits.append(msg)
            raise RuntimeError(msg)

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


CORE_INSTRUCTIONS = (
    "\n\nINSTRUCTIONS:\n"
    "You are an expert technical editor. "
    "Apply the MINIMAL set of textual edits needed for the document to follow the style guide rules above. "
    "Use the `apply_edit` tool to apply changes. "
    "IMPORTANT: \n"
    "1. The 'before' text must match the document text *character-for-character*, including whitespace. "
    "2. If an edit fails (not found), the tool will return an error. You may try to correct the snippet or skip it. "
    "3. Do NOT apply purely stylistic rewrites unless mandated by the guide. "
    "4. Ensure code blocks remain syntactically valid. "
    "5. Check the ENTIRE document. If you find multiple issues, apply them ONE BY ONE. Do NOT call `apply_edit` multiple times in parallel. Wait for the tool to return before proposing the next edit. "
    "Remember: each edit updates the document state immediately, so subsequent edits must target the NEW state of the document. "
    "6. If no changes are needed, just stop. Do NOT call `apply_edit` with identical 'before' and 'after' text.\n"
    "7. The `apply_edit` tool replaces ALL occurrences of the `before` text. "
    "If you only intend to replace one instance, ensure your `before` text is unique enough to identify it."
    "8. Provide a brief `reason` for each edit explaining which rule is being applied."
)


def update_trace_metrics(session: DocumentSession, langfuse: Any):
    """Update trace metadata with running counters."""
    if not session.trace_id:
        return

    n_accepted = session.stats["accepted"]
    n_rejected = session.stats["rejected"]
    total = n_accepted + n_rejected
    frac_rejected = round(n_rejected / total, 2) if total > 0 else 0.0

    langfuse.trace(
        id=session.trace_id,
        metadata={
            "N_accepted": n_accepted,
            "N_rejected": n_rejected,
            "frac_rejected": frac_rejected,
        },
    )


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

    if before not in session.current_content:
        msg = f"Edit failed: Text ```{before}``` not found in document."
        logger.error(msg)
        raise RuntimeError(msg)

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

            if session.trace_id and Langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
                try:
                    langfuse = Langfuse()
                    langfuse.score(
                        trace_id=session.trace_id,
                        name="user-review",
                        value=1,
                        comment=f"Accepted edit.\nBefore:\n```{before}```\nAfter->\n```{after}```\n",
                    )
                    update_trace_metrics(session, langfuse)
                except Exception as e:
                    logger.error(f"Failed to score Langfuse trace: {e}")

            return f"User accepted the proposal. {result}"
        elif decision["status"] == "modified":
            # User modified -> Apply new text, count as rejected (quality issue)
            session.stats["rejected"] += 1
            new_text = decision.get("new_text", expanded_after)
            # Apply the expanded before with the user's new text
            result = await session.apply_edit(expanded_before, new_text, reason)

            if "failed" in result.lower():
                err_msg = f"CRITICAL: User modified edit but apply failed. Result: {result}"
                logger.error(err_msg)
                raise RuntimeError(err_msg)

            if session.trace_id and Langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
                try:
                    langfuse = Langfuse()
                    langfuse.score(
                        trace_id=session.trace_id,
                        name="user-review",
                        value=0,
                        comment=f"User modified proposed edit.\nBefore:\n```{before}```\nAfter->\n```{new_text}```",
                    )
                    update_trace_metrics(session, langfuse)
                except Exception as e:
                    logger.error(f"Failed to score Langfuse trace: {e}")

            return f"User changed suggested diff to:\n```{new_text}```\nResult: {result}"
        else:
            # User rejected -> Don't apply
            session.stats["rejected"] += 1
            rejection_reason = decision.get("reason", "No reason provided")
            logger.info(f"User rejected edit. Reason: {rejection_reason}")

            if session.trace_id and Langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
                try:
                    langfuse = Langfuse()
                    langfuse.score(
                        trace_id=session.trace_id,
                        name="user-review",
                        value=0,
                        comment=f"Rejected edit.\nBefore:\n```{before}```\nAfter->\n```{after}```\nReason: {rejection_reason}",
                    )
                    update_trace_metrics(session, langfuse)
                except Exception as e:
                    logger.error(f"Failed to score Langfuse trace: {e}")

            return f"User rejected the proposal. Reason given: {rejection_reason}. Move on to the next issue."
    else:
        # Non-interactive mode: Apply immediately (no context expansion to stay faithful to agent request)
        logger.info(f"Agent proposing edit.\nBefore:\n```{before}```\nAfter->\n```{after}```\n")
        return await session.apply_edit(before, after, reason)


async def process_style_guide(
    style_guide_text: str,
    session: DocumentSession,
    callbacks: list | None = None,
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
        callbacks = []

    # Store current style guide in session for downstream use (e.g. logging)
    session.current_style_guide = style_guide_text

    # Initialize Langfuse trace if credentials exist and Langfuse is available
    if (
        Langfuse
        and LangfuseCallbackHandler
        and os.getenv("LANGFUSE_SECRET_KEY")
        and os.getenv("LANGFUSE_PUBLIC_KEY")
    ):
        try:
            # Use CallbackHandler directly as Langfuse.trace() is not available in v3
            # CallbackHandler in this version does not accept tags/version in __init__
            handler = LangfuseCallbackHandler()
            callbacks.append(handler)
            # session.trace_id remains None as we rely on CallbackHandler's internal trace creation
            logger.info("Langfuse handler initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse trace: {e}")

    @tool
    async def apply_edit(before: str, after: str, reason: str = ""):
        """
        Replaces exact text in the document.
        Args:
            before: The exact text snippet to replace (must match character-for-character, including whitespace).
            after: The replacement text.
            reason: A brief explanation of why this edit is necessary based on the style guide.
        """
        return await handle_edit_proposal(session, before, after, reason, review_callback)

    tools = [apply_edit]

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
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=50)

    logger.info("Starting agent loop...")

    await agent_executor.ainvoke(
        {
            "document": session.current_content,
        },
        config={"callbacks": callbacks},
    )
