"""Core editing logic for auto_docs_editor."""

from __future__ import annotations

import os
from collections.abc import Callable

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
except ImportError:
    Langfuse = None

from settings import MODEL_NAME, TRACE_DATASET_VERSION


class DocumentSession:
    """Manages the document state and edit history for the agent."""

    def __init__(self, content: str, seen_edits: set[tuple[str, str]]):
        self.initial_content = content
        self.current_content = content
        self.seen_edits = seen_edits  # Edits seen globally across all guides
        self.session_edits: list[tuple[str, str]] = []  # Edits applied in this session
        self.failed_edits: list[str] = []
        self.trace_id: str | None = None
        self.current_style_guide: str = ""
        # Metrics for queryability
        self.stats = {"accepted": 0, "rejected": 0}

    def apply_edit(self, before: str, after: str, reason: str = "") -> str:
        """Tool implementation to replace text."""
        if before not in self.current_content:
            msg = f"Edit failed: Text '{before}' not found in document."
            self.failed_edits.append(msg)
            return msg

        self.current_content = self.current_content.replace(before, after)
        self.session_edits.append((before, after))
        self.seen_edits.add((before, after))

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
    "5. Check the ENTIRE document. If you find multiple issues, apply MULTIPLE edits. You can call `apply_edit` multiple times in parallel. "
    "6. If no changes are needed, just stop. "
    "7. The `apply_edit` tool replaces ALL occurrences of the `before` text. "
    "If you only intend to replace one instance, ensure your `before` text is unique enough to identify it."
    "8. Provide a brief `reason` for each edit explaining which rule is being applied."
)


def process_style_guide(
    style_guide_text: str,
    session: DocumentSession,
    callbacks: list | None = None,
    review_callback: Callable[[str, str, str], dict] | None = None,
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
        guide_name: Optional name of the style guide file for tagging
    """
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    if callbacks is None:
        callbacks = []

    # Store current style guide in session for downstream use (e.g. logging)
    session.current_style_guide = style_guide_text

    # Initialize Langfuse trace if credentials exist and Langfuse is available
    if Langfuse and os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        try:
            langfuse = Langfuse()
            tags = [TRACE_DATASET_VERSION]
            if guide_name:
                tags.append(guide_name)

            trace = langfuse.trace(
                name="style-guide-process",
                version=TRACE_DATASET_VERSION,
                metadata={
                    "interactive": review_callback is not None,
                },
                tags=tags,
            )
            handler = trace.get_langchain_handler()
            callbacks.append(handler)
            session.trace_id = trace.id
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse trace: {e}")

    def update_trace_metrics(session: DocumentSession, langfuse: Langfuse):
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

    @tool
    def apply_edit(before: str, after: str, reason: str = ""):
        """
        Replaces exact text in the document.
        Args:
            before: The exact text snippet to replace (must match character-for-character, including whitespace).
            after: The replacement text.
            reason: A brief explanation of why this edit is necessary based on the style guide.
        """
        # First check if text exists (fail fast for agent)
        if before not in session.current_content:
            logger.warning(f"Edit failed: Text '{before}' not found.")
            return f"Edit failed: Text '{before}' not found in document. Please verify the snippet."

        if review_callback:
            # Interactive mode: Pause and ask user
            logger.info(f"Agent proposing edit for review: '{before[:50]}...' -> '{after[:50]}...'")
            decision = review_callback(before, after, reason)

            if decision["status"] == "accepted":
                # User accepted -> Apply
                session.stats["accepted"] += 1
                result = session.apply_edit(before, after, reason)
                if session.trace_id and Langfuse and os.getenv("LANGFUSE_SECRET_KEY"):
                    try:
                        langfuse = Langfuse()
                        langfuse.score(
                            trace_id=session.trace_id,
                            name="user-review",
                            value=1,
                            comment=f"Accepted edit: '{before[:30]}...' -> '{after[:30]}...'",
                        )
                        update_trace_metrics(session, langfuse)
                    except Exception as e:
                        logger.error(f"Failed to score Langfuse trace: {e}")

                return f"User accepted the proposal. {result}"
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
                            comment=f"Rejected edit: '{before[:30]}...' -> '{after[:30]}...'. Reason: {rejection_reason}",
                        )
                        update_trace_metrics(session, langfuse)
                    except Exception as e:
                        logger.error(f"Failed to score Langfuse trace: {e}")

                return f"User rejected the proposal. Reason given: {rejection_reason}. Move on to the next issue."
        else:
            # Non-interactive mode: Apply immediately
            logger.info(f"Agent proposing edit: '{before}' -> '{after}'")
            return session.apply_edit(before, after, reason)

    tools = [apply_edit]

    # Refactored prompt structure: Style Guide as System, Document as User
    system_message = style_guide_text + CORE_INSTRUCTIONS

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

    agent_executor.invoke(
        {
            "document": session.current_content,
        },
        config={"callbacks": callbacks},
    )
