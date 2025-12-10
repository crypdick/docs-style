#!/usr/bin/env python3
"""Interactive TUI for reviewing and applying style guide edits."""

from __future__ import annotations

import difflib
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, RichLog, Static, TextArea

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

from auto_docs_editor.core import DocumentSession, process_style_guide
from auto_docs_editor.notebook import NotebookHandler, ensure_jupytext_installed, is_notebook
from settings import FINAL_PASS_MARKER, STYLE_DIR
from utils import get_langfuse_handler, setup_logging


class DiffView(Container):
    """Widget to display a git-style unified diff with editable after content."""

    def __init__(self, before: str, after: str, reason: str = "", **kwargs):
        super().__init__(**kwargs)
        self.before = before
        self.after = after
        self.reason = reason

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        if self.reason:
            yield Label(
                f"[bold cyan]Reason:[/bold cyan] {self.reason}", classes="reason", markup=True
            )

        # Create unified diff
        diff_text = Text()

        before_lines = self.before.splitlines(keepends=False)
        after_lines = self.after.splitlines(keepends=False)

        # Use difflib to create a unified diff
        differ = difflib.Differ()
        diff = list(differ.compare(before_lines, after_lines))

        for line in diff:
            if line.startswith("- "):
                # Removed line
                diff_text.append("- ", style="bold red")
                diff_text.append(line[2:], style="red")
                diff_text.append("\n")
            elif line.startswith("+ "):
                # Added line
                diff_text.append("+ ", style="bold green")
                diff_text.append(line[2:], style="green")
                diff_text.append("\n")
            elif line.startswith("  "):
                # Context line (unchanged)
                diff_text.append("  ", style="dim")
                diff_text.append(line[2:], style="dim")
                diff_text.append("\n")
            # Skip lines starting with '?' (difflib's change indicators)

        yield Label("[bold]Diff Preview:[/bold]", markup=True)
        yield Static(diff_text, classes="diff-inline")

        yield Label("\n[bold]Edit Result (editable):[/bold]", markup=True, classes="edit-label")
        yield TextArea(
            self.after, language="markdown", theme="monokai", id="edit-area", classes="edit-area"
        )


class RejectionModal(ModalScreen[str]):
    """Modal to enter rejection reason."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Enter rejection reason (optional):"),
            TextArea(id="reason-input"),
            Horizontal(
                Button("Confirm Reject", variant="error", id="confirm"),
                Button("Cancel", variant="default", id="cancel"),
            ),
            classes="modal-content",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            reason = self.query_one("#reason-input", TextArea).text
            self.dismiss(reason)
        else:
            self.dismiss(None)


class AutoDocsEditorTUI(App):
    """TUI application for reviewing style guide edits."""

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        Binding("a", "accept", "Accept & Apply", priority=True),
        Binding("r", "reject", "Reject", priority=True),
        Binding("s", "skip_guide", "Skip Guide", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        document_path: Path,
        style_pages: list[Path],
        seen_edits: set[tuple[str, str]],
        is_notebook: bool = False,
        notebook_handler: NotebookHandler | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.document_path = document_path
        self.style_pages = style_pages
        self.seen_edits = seen_edits
        self.is_notebook = is_notebook
        self.notebook_handler = notebook_handler
        self.current_page_idx = 0
        self.session: DocumentSession | None = None
        self.total_accepted = 0
        self.total_rejected = 0
        self.callbacks = []

        # Synchronization primitives for thread <-> UI communication
        self.review_event = threading.Event()
        self.review_decision: dict | None = None

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
                yield RichLog(id="activity-log", wrap=True, highlight=False, markup=True)

            with Horizontal(id="button-panel"):
                yield Button(
                    "Accept & Apply (a)",
                    variant="success",
                    id="btn-accept",
                    classes="button-accept",
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
        self.start_processing_guide()

    @work(exclusive=True, thread=True)
    def start_processing_guide(self) -> None:
        """Process the current style guide in a worker thread."""
        if self.current_page_idx >= len(self.style_pages):
            self.call_from_thread(self.show_completion)
            return

        page_path = self.style_pages[self.current_page_idx]
        self.call_from_thread(
            self.update_status,
            f"[bold]Style Guide:[/bold] {page_path.name} ({self.current_page_idx + 1}/{len(self.style_pages)})",
        )

        # Log to activity log
        self.call_from_thread(
            self.log_activity, f"[bold cyan]Processing:[/bold cyan] {page_path.name}"
        )

        # Read current document content
        doc_text = self.document_path.read_text(encoding="utf-8")
        style_text = page_path.read_text(encoding="utf-8")

        # Create session and process guide
        self.session = DocumentSession(doc_text, self.seen_edits)

        logger.info(f"Processing style guide: {page_path.name}")

        try:
            # Process with interactive callback
            process_style_guide(
                style_text,
                self.session,
                callbacks=self.callbacks,
                review_callback=self.ask_user_review,
                guide_name=page_path.name,
            )
        except Exception as e:
            logger.error(f"Error processing style guide: {e}")
            self.call_from_thread(self.log_activity, f"[bold red]Error:[/bold red] {e}")
            self.call_from_thread(self.show_error, str(e))
            return

        # Guide processing finished
        self.call_from_thread(self.save_and_next_guide)

    def ask_user_review(self, before: str, after: str, reason: str) -> dict:
        """Callback invoked by the agent (in worker thread) to request user review.

        Blocks until the user interacts with the UI.
        """
        # Clear previous decision
        self.review_decision = None
        self.review_event.clear()

        # Update UI to show the diff
        self.call_from_thread(self.show_diff_ui, before, after, reason)

        # Wait for user action
        self.review_event.wait()

        # Return the user's decision
        return self.review_decision or {"status": "rejected", "reason": "Cancelled or Interrupted"}

    def show_diff_ui(self, before: str, after: str, reason: str) -> None:
        """Update the UI to show the diff (runs on main thread via call_from_thread)."""
        # Store current proposal for later comparison
        self.current_proposal = (before, after, reason)

        self.query_one("#progress-label", Label).update(
            f"[bold]Accepted:[/bold] {self.total_accepted} | "
            f"[bold]Rejected:[/bold] {self.total_rejected}"
        )

        # Clear activity log and show diff
        diff_container = self.query_one("#diff-container", VerticalScroll)
        diff_container.remove_children()
        diff_container.mount(DiffView(before, after, reason))

    def update_status(self, text: str) -> None:
        self.query_one("#status-label", Label).update(text)

    def log_activity(self, text: str) -> None:
        try:
            activity_log = self.query_one("#activity-log", RichLog)
            activity_log.write(text)
        except Exception:
            pass

    def action_accept(self) -> None:
        """Handle accept action from UI."""
        if not self.review_event.is_set():
            # Get edited text if any
            try:
                edit_area = self.query_one("#edit-area", TextArea)
                edited_after = edit_area.text
            except Exception:
                edited_after = self.current_proposal[
                    1
                ]  # Should not happen given DiffView structure

            original_after = self.current_proposal[1]

            if edited_after != original_after:
                # User modified the text -> Count as rejection per requirements
                self.total_rejected += 1
                self.review_decision = {"status": "modified", "new_text": edited_after}

                # Re-mount log
                diff_container = self.query_one("#diff-container", VerticalScroll)
                diff_container.remove_children()
                diff_container.mount(
                    RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
                )
                self.log_activity("[yellow]⚠ Accepted with changes (counted as rejection)[/yellow]")
            else:
                self.total_accepted += 1
                self.review_decision = {"status": "accepted"}

                # Re-mount log
                diff_container = self.query_one("#diff-container", VerticalScroll)
                diff_container.remove_children()
                diff_container.mount(
                    RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
                )
                self.log_activity("[green]✓ Accepted[/green]")

            self.review_event.set()

    def action_reject(self) -> None:
        """Handle reject action from UI."""
        if not self.review_event.is_set():

            def finalize_rejection(reason: str | None) -> None:
                if reason is None:
                    return  # Cancelled modal

                self.total_rejected += 1
                self.review_decision = {"status": "rejected", "reason": reason}
                self.review_event.set()

                # Re-mount log
                diff_container = self.query_one("#diff-container", VerticalScroll)
                diff_container.remove_children()
                diff_container.mount(
                    RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
                )
                self.log_activity(f"[yellow]⊘ Rejected[/yellow] (Reason: {reason})")

            self.push_screen(RejectionModal(), finalize_rejection)

    def action_skip_guide(self) -> None:
        """Skip the rest of the current guide."""
        # For the Agent loop, skipping is tricky. We can just reject with a special reason?
        # Or we can cancel the future.
        # Simplest is to reject this one and set a flag to reject all future ones?
        # Or just stop the agent?
        # `process_style_guide` doesn't have a clean "abort" signal exposed to callback other than maybe raising exception.
        # Let's reject current with "Skipping guide".
        if not self.review_event.is_set():
            self.review_decision = {"status": "rejected", "reason": "User skipped remaining edits."}
            # Ideally we should signal the loop to stop.
            # We can do this by raising an exception in the callback?
            # For now, just reject.
            self.review_event.set()
            self.log_activity("[dim]⏭ Skipped[/dim]")

    def save_and_next_guide(self) -> None:
        """Save changes and move to the next guide."""
        # Capture session info before moving to next guide
        had_changes = False
        edits_count = 0
        if self.session and self.session.current_content != self.session.initial_content:
            self.document_path.write_text(self.session.current_content, encoding="utf-8")
            edits_count = len(self.session.session_edits)
            had_changes = True
            logger.success(f"Document updated with {edits_count} edits.")

            # Sync notebook in background if applicable
            if self.is_notebook and self.notebook_handler:
                self.sync_notebook_background()

        # Move to next guide
        self.next_guide()

        # Log save status
        if had_changes:
            save_msg = f"💾 Saved {edits_count} edits from previous guide"
            if self.is_notebook:
                save_msg += " (syncing to notebook...)"
            self.log_activity(f"[bold green]{save_msg}[/bold green]")
        else:
            self.log_activity("[dim]No changes to save from previous guide[/dim]")

    @work(exclusive=False, thread=True)
    def sync_notebook_background(self) -> None:
        """Sync markdown changes back to notebook in a background worker."""
        if not self.notebook_handler:
            return

        try:
            logger.info("Background sync: Syncing Markdown to notebook...")
            self.notebook_handler.sync_back()
            logger.success("Background sync: Successfully synced to notebook")
            self.call_from_thread(self._on_sync_complete, success=True)
        except Exception as e:
            logger.error(f"Background sync failed: {e}")
            self.call_from_thread(self._on_sync_complete, success=False, error=str(e))

    def _on_sync_complete(self, success: bool, error: str = "") -> None:
        """Called when background sync completes (runs on main thread)."""
        if success:
            self.log_activity("[dim]✓ Notebook synced[/dim]")
        else:
            self.log_activity(f"[bold red]✗ Notebook sync failed: {error}[/bold red]")

    def next_guide(self) -> None:
        """Move to the next style guide."""
        self.current_page_idx += 1

        # Re-initialize UI state
        diff_container = self.query_one("#diff-container", VerticalScroll)
        diff_container.remove_children()
        activity_log = RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
        diff_container.mount(activity_log)

        # Start processing next guide
        self.start_processing_guide()

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

        activity_log = RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
        diff_container.mount(activity_log)

        activity_log.write("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        activity_log.write("[bold green]✓ All style guides processed![/bold green]")
        activity_log.write("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        activity_log.write(f"[bold]Total Accepted:[/bold] [green]{self.total_accepted}[/green]")
        activity_log.write(f"[bold]Total Rejected:[/bold] [yellow]{self.total_rejected}[/yellow]")
        if self.is_notebook:
            activity_log.write("\n[bold green]Note:[/bold green] All changes synced to notebook.")
        activity_log.write("\n[dim]Press 'q' to quit.[/dim]")

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
        self.action_accept()

    @on(Button.Pressed, "#btn-reject")
    def on_reject_pressed(self) -> None:
        self.action_reject()

    @on(Button.Pressed, "#btn-skip")
    def on_skip_pressed(self) -> None:
        self.action_skip_guide()

    @on(Button.Pressed, "#btn-quit")
    def on_quit_pressed(self) -> None:
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

    # Setup logging (TUI mode - only log to file, not to stdout)
    log_file = setup_logging(tui_mode=True)
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
    app = AutoDocsEditorTUI(
        target_path,
        style_pages,
        seen_edits,
        is_notebook=notebook_handler is not None,
        notebook_handler=notebook_handler,
    )
    app.run()

    # Final sync back to notebook if needed (in case there are pending changes)
    if notebook_handler:
        logger.info("Final sync: Syncing changes back to notebook...")
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
