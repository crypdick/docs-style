#!/usr/bin/env python3
"""Interactive TUI for reviewing and applying style guide edits."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from rich.syntax import Syntax
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static

from auto_docs_editor.core import DocumentSession, process_style_guide
from auto_docs_editor.notebook import NotebookHandler, ensure_jupytext_installed, is_notebook
from settings import FINAL_PASS_MARKER, STYLE_DIR
from utils import get_langfuse_handler, setup_logging


class DiffView(Static):
    """Widget to display a diff with before/after comparison."""

    def __init__(self, before: str, after: str, reason: str = "", **kwargs):
        super().__init__(**kwargs)
        self.before = before
        self.after = after
        self.reason = reason

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        if self.reason:
            yield Label(f"[bold cyan]Reason:[/bold cyan] {self.reason}", classes="reason")

        yield Label("[bold red]Before:[/bold red]", classes="diff-label")
        yield Static(
            Syntax(self.before, "markdown", theme="monokai", line_numbers=False),
            classes="diff-before",
        )

        yield Label("[bold green]After:[/bold green]", classes="diff-label")
        yield Static(
            Syntax(self.after, "markdown", theme="monokai", line_numbers=False),
            classes="diff-after",
        )


class AutoDocsEditorTUI(App):
    """TUI application for reviewing style guide edits."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        height: 100%;
        width: 100%;
    }

    #info-panel {
        height: auto;
        padding: 1;
        background: $boost;
        border: solid $primary;
    }

    #diff-container {
        height: 1fr;
        padding: 1;
        border: solid $accent;
    }

    #button-panel {
        height: auto;
        padding: 1;
        background: $panel;
    }

    .diff-label {
        margin-top: 1;
        margin-bottom: 1;
    }

    .diff-before {
        background: $error 20%;
        padding: 1;
        border: solid $error;
    }

    .diff-after {
        background: $success 20%;
        padding: 1;
        border: solid $success;
    }

    .reason {
        padding: 1;
        background: $accent 20%;
        margin-bottom: 1;
    }

    Button {
        margin: 0 1;
    }

    .button-accept {
        background: $success;
    }

    .button-reject {
        background: $error;
    }

    .button-skip {
        background: $warning;
    }
    """

    BINDINGS = [
        Binding("a", "accept", "Accept", priority=True),
        Binding("r", "reject", "Reject", priority=True),
        Binding("s", "skip_guide", "Skip Guide", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        document_path: Path,
        style_pages: list[Path],
        seen_edits: set[tuple[str, str]],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.document_path = document_path
        self.style_pages = style_pages
        self.seen_edits = seen_edits
        self.current_page_idx = 0
        self.current_edit_idx = 0
        self.session: DocumentSession | None = None
        self.total_accepted = 0
        self.total_rejected = 0
        self.callbacks = []

        handler = get_langfuse_handler()
        if handler:
            self.callbacks.append(handler)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Vertical(id="main-container"):
            with Container(id="info-panel"):
                yield Label("", id="status-label")
                yield Label("", id="progress-label")

            with VerticalScroll(id="diff-container"):
                yield Label("Loading...", id="diff-content")

            with Horizontal(id="button-panel"):
                yield Button(
                    "Accept (a)", variant="success", id="btn-accept", classes="button-accept"
                )
                yield Button(
                    "Reject (r)", variant="error", id="btn-reject", classes="button-reject"
                )
                yield Button(
                    "Skip Guide (s)", variant="warning", id="btn-skip", classes="button-skip"
                )
                yield Button("Quit (q)", variant="default", id="btn-quit")

        yield Footer()

    def on_mount(self) -> None:
        """Process the first style guide when the app starts."""
        self.process_current_guide()

    def process_current_guide(self) -> None:
        """Process the current style guide and collect proposed edits."""
        if self.current_page_idx >= len(self.style_pages):
            self.show_completion()
            return

        page_path = self.style_pages[self.current_page_idx]
        self.query_one("#status-label", Label).update(
            f"[bold]Style Guide:[/bold] {page_path.name} ({self.current_page_idx + 1}/{len(self.style_pages)})"
        )

        # Read current document content
        doc_text = self.document_path.read_text(encoding="utf-8")
        style_text = page_path.read_text(encoding="utf-8")

        # Create session and process guide
        self.session = DocumentSession(doc_text, self.seen_edits)

        logger.info(f"Processing style guide: {page_path.name}")

        try:
            # Process in interactive mode to collect proposed edits
            process_style_guide(
                style_text, self.session, callbacks=self.callbacks, interactive=True
            )
        except Exception as e:
            logger.error(f"Error processing style guide: {e}")
            self.show_error(str(e))
            return

        # Reset edit index for new guide
        self.current_edit_idx = 0

        if not self.session.pending_edits:
            logger.info("No edits proposed for this guide.")
            self.next_guide()
        else:
            logger.info(f"Collected {len(self.session.pending_edits)} proposed edits.")
            self.show_current_edit()

    def show_current_edit(self) -> None:
        """Display the current edit for review."""
        if not self.session or self.current_edit_idx >= len(self.session.pending_edits):
            self.save_and_next_guide()
            return

        before, after, reason = self.session.pending_edits[self.current_edit_idx]

        self.query_one("#progress-label", Label).update(
            f"[bold]Edit:[/bold] {self.current_edit_idx + 1}/{len(self.session.pending_edits)} | "
            f"Accepted: {self.total_accepted} | Rejected: {self.total_rejected}"
        )

        # Replace diff content
        diff_container = self.query_one("#diff-container", VerticalScroll)
        diff_container.remove_children()
        diff_container.mount(DiffView(before, after, reason))

    def action_accept(self) -> None:
        """Accept the current edit."""
        if not self.session or self.current_edit_idx >= len(self.session.pending_edits):
            return

        before, after, reason = self.session.pending_edits[self.current_edit_idx]
        result = self.session.apply_edit(before, after, reason)

        if "successfully" in result:
            self.total_accepted += 1
            logger.info(f"Edit accepted: '{before[:50]}...' -> '{after[:50]}...'")
        else:
            logger.error(f"Failed to apply edit: {result}")

        self.current_edit_idx += 1
        self.show_current_edit()

    def action_reject(self) -> None:
        """Reject the current edit."""
        if not self.session or self.current_edit_idx >= len(self.session.pending_edits):
            return

        before, after, _ = self.session.pending_edits[self.current_edit_idx]
        self.total_rejected += 1
        logger.info(f"Edit rejected: '{before[:50]}...' -> '{after[:50]}...'")

        self.current_edit_idx += 1
        self.show_current_edit()

    def action_skip_guide(self) -> None:
        """Skip the rest of the current guide."""
        logger.info("Skipping remaining edits in current guide.")
        self.save_and_next_guide()

    def save_and_next_guide(self) -> None:
        """Save changes and move to the next guide."""
        if self.session and self.session.current_content != self.session.initial_content:
            self.document_path.write_text(self.session.current_content, encoding="utf-8")
            logger.success(f"Document updated with {len(self.session.session_edits)} edits.")

        self.next_guide()

    def next_guide(self) -> None:
        """Move to the next style guide."""
        self.current_page_idx += 1
        self.process_current_guide()

    def show_completion(self) -> None:
        """Show completion message."""
        self.query_one("#status-label", Label).update(
            "[bold green]✓ All style guides processed![/bold green]"
        )
        self.query_one("#progress-label", Label).update(
            f"[bold]Total Accepted:[/bold] {self.total_accepted} | "
            f"[bold]Total Rejected:[/bold] {self.total_rejected}"
        )

        diff_container = self.query_one("#diff-container", VerticalScroll)
        diff_container.remove_children()
        diff_container.mount(
            Label(
                "\n\n[bold cyan]All style guides have been processed![/bold cyan]\n\n"
                "Press 'q' to quit.",
                id="diff-content",
            )
        )

    def show_error(self, error: str) -> None:
        """Show an error message."""
        diff_container = self.query_one("#diff-container", VerticalScroll)
        diff_container.remove_children()
        diff_container.mount(
            Label(
                f"\n\n[bold red]Error:[/bold red]\n\n{error}\n\n"
                "Press 'q' to quit or 's' to skip to next guide.",
                id="diff-content",
            )
        )

    @on(Button.Pressed, "#btn-accept")
    def on_accept_pressed(self) -> None:
        """Handle accept button press."""
        self.action_accept()

    @on(Button.Pressed, "#btn-reject")
    def on_reject_pressed(self) -> None:
        """Handle reject button press."""
        self.action_reject()

    @on(Button.Pressed, "#btn-skip")
    def on_skip_pressed(self) -> None:
        """Handle skip button press."""
        self.action_skip_guide()

    @on(Button.Pressed, "#btn-quit")
    def on_quit_pressed(self) -> None:
        """Handle quit button press."""
        self.action_quit()


def run() -> None:
    """Entry point for the TUI application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive TUI for applying Google style guide edits.",
    )
    parser.add_argument(
        "markdown_document",
        help="Path to the markdown document or Jupyter notebook (.ipynb) to process.",
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
            f"with the '{FINAL_PASS_MARKER}' symbol."
        ),
    )
    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging()
    logger.info(f"TUI session started. Log file: {log_file}")

    # Load environment
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is not set. Provide it in the environment or .env file.")
        sys.exit(1)

    # Validate document path
    target_path = Path(args.markdown_document).expanduser().resolve()
    if not target_path.is_file():
        logger.error(f"Error: {target_path} is not a file.")
        sys.exit(1)

    # Handle Jupyter notebooks
    notebook_handler = None
    original_target = target_path

    if is_notebook(target_path):
        if not ensure_jupytext_installed():
            logger.error("Jupytext is not installed. Install it with: uv add jupytext")
            sys.exit(1)

        logger.info(f"Detected Jupyter notebook: {target_path}")
        notebook_handler = NotebookHandler(target_path)

        try:
            # Pair notebook with Markdown (will error if .md already exists)
            target_path = notebook_handler.ensure_paired()
            logger.info(f"Working with paired Markdown: {target_path}")
        except RuntimeError as e:
            logger.error(str(e))
            sys.exit(1)

    # Get style pages
    style_pages = sorted(STYLE_DIR.glob("*.md"), key=lambda p: p.name)

    if args.final_pass:
        logger.info("Processing final pass style rules only.")
        style_pages = [p for p in style_pages if p.stem.endswith(FINAL_PASS_MARKER)]

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

    # Run the TUI
    seen_edits: set[tuple[str, str]] = set()
    app = AutoDocsEditorTUI(target_path, style_pages, seen_edits)
    app.run()

    # Sync back to notebook if needed
    if notebook_handler:
        logger.info("Syncing changes back to notebook...")
        try:
            notebook_handler.sync_back()
            logger.success(f"Successfully updated notebook: {original_target}")
            logger.info(f"Paired Markdown preserved at: {target_path}")
        except RuntimeError as e:
            logger.error(f"Failed to sync back to notebook: {e}")
            logger.warning(f"Markdown edits are preserved in: {target_path}")
            sys.exit(1)


if __name__ == "__main__":
    run()
