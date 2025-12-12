"""Controller logic for the auto_docs_editor workflow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from auto_docs_editor.core import DocumentSession
from auto_docs_editor.core_vale import enforce_vale_style
from auto_docs_editor.notebook import NotebookHandler
from utils import read_text_async, write_text_async


class ReviewController:
    """Manages the state and workflow of the review process."""

    def __init__(
        self,
        document_path: Path,
        style_pages: list[Path],
        seen_edits: set[tuple[str, str]],
        notebook_handler: NotebookHandler | None = None,
    ):
        self.document_path = document_path
        self.style_pages = style_pages
        self.seen_edits = seen_edits
        self.notebook_handler = notebook_handler
        self.is_notebook = notebook_handler is not None

        self.current_page_idx = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.session: DocumentSession | None = None

    @property
    def current_guide_path(self) -> Path | None:
        """Return the path to the current style guide file."""
        if 0 <= self.current_page_idx < len(self.style_pages):
            return self.style_pages[self.current_page_idx]
        return None

    @property
    def is_finished(self) -> bool:
        """Return True if all guides have been processed."""
        return self.current_page_idx >= len(self.style_pages)

    @property
    def progress_str(self) -> str:
        """Return a string representing progress (e.g., '1/5')."""
        return f"{self.current_page_idx + 1}/{len(self.style_pages)}"

    async def prepare_session(self, on_apply: Callable[[str], Any]) -> DocumentSession:
        """Read files and create a new DocumentSession for the current guide."""
        if not self.current_guide_path:
            raise ValueError("No current guide available.")

        doc_text = await read_text_async(self.document_path, encoding="utf-8")

        # Read the document in between each edit, so that any manual edits that
        # are made out-of-band are not lost.
        async def content_provider() -> str:
            return await read_text_async(self.document_path, encoding="utf-8")

        self.session = DocumentSession(
            doc_text, self.seen_edits, on_apply=on_apply, content_provider=content_provider
        )
        return self.session

    async def get_style_guide_content(self) -> str:
        """Read the content of the current style guide."""
        if not self.current_guide_path:
            raise ValueError("No current guide available.")
        return await read_text_async(self.current_guide_path, encoding="utf-8")

    async def save_if_changed(self) -> tuple[bool, int]:
        """Save the document if it has changed in the current session.

        Returns:
            Tuple of (had_changes, edits_count)
        """
        if not self.session:
            return False, 0

        if self.session.current_content != self.session.initial_content:
            await write_text_async(
                self.document_path, self.session.current_content, encoding="utf-8"
            )
            edits_count = len(self.session.session_edits)
            return True, edits_count

        return False, 0

    def sync_notebook(self) -> None:
        """Sync changes back to the notebook (blocking/synchronous version)."""
        if self.notebook_handler:
            self.notebook_handler.sync_back()

    def advance(self) -> None:
        """Move to the next style guide."""
        self.current_page_idx += 1
        self.session = None

    def run_vale(self) -> None:
        """Run Vale enforcement on the document."""
        enforce_vale_style(self.document_path)
