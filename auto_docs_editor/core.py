"""Core editing logic for auto_docs_editor."""

from __future__ import annotations

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    # Fallback for newer langchain versions (1.1.0+)
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from loguru import logger

from settings import MODEL_NAME


class DocumentSession:
    """Manages the document state and edit history for the agent."""

    def __init__(self, content: str, seen_edits: set[tuple[str, str]]):
        self.initial_content = content
        self.current_content = content
        self.seen_edits = seen_edits  # Edits seen globally across all guides
        self.session_edits: list[tuple[str, str]] = []  # Edits applied in this session
        self.failed_edits: list[str] = []
        self.pending_edits: list[tuple[str, str, str]] = []  # (before, after, reason) for TUI mode

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

    def propose_edit(self, before: str, after: str, reason: str = "") -> str:
        """Queue an edit for review (TUI mode)."""
        if before not in self.current_content:
            msg = f"Edit failed: Text '{before}' not found in document."
            self.failed_edits.append(msg)
            return msg

        if (before, after) not in [(b, a) for b, a, _ in self.pending_edits]:
            self.pending_edits.append((before, after, reason))

        return "Edit proposed for review."


def process_style_guide(
    style_guide_text: str,
    session: DocumentSession,
    callbacks: list | None = None,
    interactive: bool = False,
) -> None:
    """Run the agent loop to apply edits from the style guide.

    Args:
        style_guide_text: The style guide content
        session: DocumentSession to track edits
        callbacks: Optional list of callbacks (e.g., Langfuse)
        interactive: If True, edits are queued for review instead of applied immediately
    """
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    if callbacks is None:
        callbacks = []

    if interactive:

        @tool
        def apply_edit(before: str, after: str):
            """
            Proposes a text replacement for user review.
            Args:
                before: The exact text snippet to replace (must match character-for-character, including whitespace).
                after: The replacement text.
            """
            logger.info(f"Agent proposing edit for review: '{before[:50]}...' -> '{after[:50]}...'")
            return session.propose_edit(before, after)
    else:

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
