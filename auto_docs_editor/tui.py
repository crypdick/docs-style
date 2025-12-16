#!/usr/bin/env python3
"""Interactive TUI for reviewing and applying style guide edits."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, RichLog

from auto_docs_editor.controller import ReviewController
from auto_docs_editor.core import process_style_guide
from auto_docs_editor.widgets import DiffView, RejectionModal
from auto_docs_editor.workflow import (
    get_style_guides,
    load_and_validate_target,
    setup_environment,
)
from settings import FINAL_PASS_MARKER
from utils import get_langfuse_handler, setup_logging, write_text_async


class AutoDocsEditorTUI(App):
    """TUI application for reviewing style guide edits."""

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        Binding("a", "accept", "Accept & Apply", priority=True),
        Binding("r", "reject", "Reject", priority=True),
        Binding("i", "ignore", "Ignore", priority=True),
        Binding("s", "skip_guide", "Skip Guide", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, controller: ReviewController, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.callbacks = []

        # Synchronization primitives for thread <-> UI communication
        self.review_event = asyncio.Event()
        self.review_lock = asyncio.Lock()
        self.review_decision: dict | None = None
        self.is_quitting = False
        self.current_proposal: tuple[str, str, str] | None = None

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
                    "Ignore (i)", variant="primary", id="btn-ignore", classes="button-ignore"
                )
                yield Button(
                    "Skip Guide (s)", variant="warning", id="btn-skip", classes="button-skip"
                )
                yield Button("Quit (q)", variant="default", id="btn-quit")

        yield Footer()

    def on_mount(self) -> None:
        """Run initial Vale check and then process the first style guide."""
        self.run_initial_vale_check()

    async def on_edit_applied(self, content: str) -> None:
        """Callback for when an edit is applied to the session."""
        # Write directly to file - fail fast if this errors
        await write_text_async(self.controller.document_path, content, encoding="utf-8")

        # Sync notebook if needed
        if self.controller.is_notebook:
            self.sync_notebook_background()

    @work
    async def start_processing_guide(self) -> None:
        """Process the current style guide in a worker."""
        if self.controller.is_finished:
            await self.show_completion()
            return

        guide_path = self.controller.current_guide_path
        if not guide_path:
            return  # Should not happen given is_finished check

        self.update_status(
            f"[bold]Style Guide:[/bold] {guide_path.name} ({self.controller.progress_str})",
        )

        # Log to activity log
        self.log_activity(f"[bold cyan]Processing:[/bold cyan] {guide_path.name}")

        try:
            # Create session via controller
            await self.controller.prepare_session(on_apply=self.on_edit_applied)
            style_text = await self.controller.get_style_guide_content()
            session = self.controller.session
            if not session:
                raise RuntimeError("Session failed to initialize")

            logger.info(f"Processing style guide: {guide_path.name}")

            # Process with interactive callback
            await process_style_guide(
                style_text,
                session,
                callbacks=self.callbacks,
                review_callback=self.ask_user_review,
                guide_name=guide_path.name,
            )
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            logger.info("Processing interrupted by user shutdown.")
            return
        except Exception as e:
            logger.error(f"Error processing style guide: {e}")
            self.log_activity(f"[bold red]Error:[/bold red] {e}")
            await self.show_error(str(e))
            return

        # Guide processing finished
        await self.save_and_next_guide()

    async def ask_user_review(self, before: str, after: str, reason: str) -> dict:
        """Callback invoked by the agent to request user review."""
        async with self.review_lock:
            if self.is_quitting:
                raise asyncio.CancelledError("Application quitting")

            # Clear previous decision
            self.review_decision = None
            self.review_event.clear()

            # Wait for RejectionModal to fully dismiss if it was just active
            # This prevents race conditions where the UI updates while the modal is still closing
            while True:
                try:
                    is_modal = self.is_rejection_modal_active()
                    if not is_modal:
                        break
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error checking active screen: {e}")
                    break

            # Update UI to show the diff
            # Must run on main thread since we are in a worker here
            try:
                await self.show_diff_ui(before, after, reason)
            except Exception as e:
                logger.error(f"Error showing diff UI: {e}")

            # Wait for user action
            logger.info("ask_user_review: Waiting for user review...")
            await self.review_event.wait()
            logger.info("ask_user_review: User review received.")

            if self.is_quitting:
                raise asyncio.CancelledError("Application quitting")

            # Return the user's decision
            return self.review_decision or {
                "status": "rejected",
                "reason": "Cancelled or Interrupted",
            }

    def is_rejection_modal_active(self) -> bool:
        """Check if the RejectionModal is the active screen."""
        from auto_docs_editor.widgets import RejectionModal

        return isinstance(self.screen, RejectionModal)

    async def show_diff_ui(self, before: str, after: str, reason: str) -> None:
        """Update the UI to show the diff (runs on main thread via call_from_thread)."""
        logger.info("show_diff_ui: Updating UI with diff.")
        # Store current proposal for later comparison
        self.current_proposal = (before, after, reason)

        self.update_stats_label()

        # Clear activity log and show diff
        diff_container = self.query_one("#diff-container", VerticalScroll)
        await diff_container.remove_children()
        await diff_container.mount(DiffView(before, after, reason))

    def update_status(self, text: str) -> None:
        self.query_one("#status-label", Label).update(text)

    def update_stats_label(self) -> None:
        """Update the accepted/rejected stats label."""
        self.query_one("#progress-label", Label).update(
            f"[bold]Accepted:[/bold] {self.controller.total_accepted} | "
            f"[bold]Rejected:[/bold] {self.controller.total_rejected}"
        )

    def log_activity(self, text: str) -> None:
        try:
            activity_log = self.query_one("#activity-log", RichLog)
            activity_log.write(text)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-accept":
            self.action_accept()
        elif event.button.id == "btn-reject":
            self.action_reject()
        elif event.button.id == "btn-ignore":
            self.action_ignore()
        elif event.button.id == "btn-skip":
            self.action_skip_guide()
        elif event.button.id == "btn-quit":
            self.action_quit()

    def action_accept(self) -> None:
        """Handle accept action from UI."""
        if not self.review_event.is_set() and self.current_proposal:
            # Get edited text if any
            try:
                # Use query().last() to handle potential race condition where old widget is not yet removed
                edit_area = self.query("TextArea.edit-area").last()
                edited_after = edit_area.text
            except Exception as e:
                logger.error(f"Failed to retrieve edited text: {e}")
                edited_after = self.current_proposal[1]

            original_after = self.current_proposal[1]

            if edited_after != original_after:
                # User modified the text -> Count as rejection per requirements
                self.controller.total_rejected += 1
                self.review_decision = {"status": "modified", "new_text": edited_after}
                self.log_activity("[bold yellow]✎ Modified & Applied[/bold yellow]")
            else:
                self.controller.total_accepted += 1
                self.review_decision = {"status": "accepted"}
                self.log_activity("[bold green]✓ Accepted[/bold green]")

            self.update_stats_label()
            self.review_event.set()

    def action_reject(self) -> None:
        """Handle reject action from UI."""
        if not self.review_event.is_set():

            def finalize_rejection(reason: str | None) -> None:
                if reason is None:
                    return  # Cancelled modal

                self.controller.total_rejected += 1
                self.review_decision = {"status": "rejected", "reason": reason}
                self.log_activity(f"[bold red]✗ Rejected:[/bold red] {reason}")
                self.update_stats_label()
                self.review_event.set()

            self.push_screen(RejectionModal(), finalize_rejection)

    def action_ignore(self) -> None:
        """Handle ignore action (skip single edit) from UI."""
        if not self.review_event.is_set():
            self.controller.total_rejected += 1
            self.review_decision = {"status": "rejected", "reason": "Ignored by user"}
            self.log_activity("[bold yellow]↷ Ignored[/bold yellow]")
            self.update_stats_label()
            self.review_event.set()

    def action_skip_guide(self) -> None:
        """Skip the rest of the current guide."""
        if not self.review_event.is_set():
            self.review_decision = {"status": "rejected", "reason": "User skipped remaining edits."}
            self.review_event.set()
            self.log_activity("[dim]⏭ Skipped[/dim]")

    def action_quit(self) -> None:
        """Handle quit action."""
        self.is_quitting = True
        # Unblock any waiting threads
        if not self.review_event.is_set():
            self.review_decision = {"status": "rejected", "reason": "Application quitting"}
            self.review_event.set()

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        self.exit()

    async def save_and_next_guide(self) -> None:
        """Save changes and move to the next guide."""
        try:
            had_changes, edits_count = await self.controller.save_if_changed()

            if had_changes:
                save_msg = f"💾 Saved {edits_count} edits from previous guide"
                if self.controller.is_notebook:
                    save_msg += " (syncing to notebook...)"
                self.log_activity(f"[bold green]{save_msg}[/bold green]")

                # Sync notebook in background if applicable
                if self.controller.is_notebook:
                    self.sync_notebook_background()
            else:
                self.log_activity("[dim]No changes to save from previous guide[/dim]")

        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            await self.show_error(f"Failed to save document: {e}")
            return

        # Move to next guide
        self.controller.advance()

        # Re-initialize UI state
        diff_container = self.query_one("#diff-container", VerticalScroll)
        await diff_container.remove_children()
        activity_log = RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
        await diff_container.mount(activity_log)

        # Start processing next guide
        self.start_processing_guide()

    @work(exclusive=False, thread=True)
    def sync_notebook_background(self) -> None:
        """Sync markdown changes back to notebook in a background worker."""
        try:
            logger.info("Background sync: Syncing Markdown to notebook...")
            self.controller.sync_notebook()
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

    async def show_completion(self) -> None:
        """Show completion message."""
        self.query_one("#status-label", Label).update(
            "[bold green]✓ All style guides processed![/bold green]"
        )
        self.query_one("#progress-label", Label).update(
            f"[bold]Total Accepted:[/bold] {self.controller.total_accepted} | "
            f"[bold]Total Rejected:[/bold] {self.controller.total_rejected}"
        )

        diff_container = self.query_one("#diff-container", VerticalScroll)
        await diff_container.remove_children()

        activity_log = RichLog(id="activity-log", wrap=True, highlight=False, markup=True)
        await diff_container.mount(activity_log)

        activity_log.write("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        activity_log.write("[bold green]✓ All style guides processed![/bold green]")
        activity_log.write("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        activity_log.write(
            f"[bold]Total Accepted:[/bold] [green]{self.controller.total_accepted}[/green]"
        )
        activity_log.write(
            f"[bold]Total Rejected:[/bold] [yellow]{self.controller.total_rejected}[/yellow]"
        )

        # Run Vale enforcement
        activity_log.write("\n[bold]Running Vale enforcement...[/bold]")
        self.run_vale_enforcement()

    @work(exclusive=True, thread=True)
    def run_initial_vale_check(self) -> None:
        """Run initial Vale check before processing style guides."""
        self.call_from_thread(
            self.log_activity, "[bold cyan]Running initial Vale check...[/bold cyan]"
        )
        try:
            self.controller.run_vale()
            self.call_from_thread(
                self.log_activity, "[green]✓ Initial Vale check complete.[/green]"
            )
        except Exception as e:
            self.call_from_thread(
                self.log_activity, f"[bold red]✗ Initial Vale check failed: {e}[/bold red]"
            )
            raise e

        # After Vale check, start processing guides (call as a worker method)
        self.start_processing_guide()

    @work(exclusive=True, thread=True)
    def run_vale_enforcement(self) -> None:
        """Run Vale enforcement in background and log to TUI."""
        self.call_from_thread(self.log_activity, "\n[bold]Starting Vale enforcement...[/bold]")
        try:
            self.controller.run_vale()
            self.call_from_thread(self.log_activity, "[green]✓ Vale enforcement complete.[/green]")
        except Exception as e:
            self.call_from_thread(
                self.log_activity, f"[bold red]✗ Vale enforcement failed: {e}[/bold red]"
            )

        if self.controller.is_notebook:
            self.call_from_thread(
                self.log_activity,
                "\n[bold green]Note:[/bold green] All changes synced to notebook.",
            )
        self.call_from_thread(self.log_activity, "\n[dim]Press 'q' to quit.[/dim]")

    async def show_error(self, error: str) -> None:
        """Show an error message."""
        diff_container = self.query_one("#diff-container", VerticalScroll)
        await diff_container.remove_children()
        await diff_container.mount(
            Label(
                f"\n\n[bold red]Error:[/bold red]\n\n{error}\n\n"
                "Press 'q' to quit or 's' to skip to next guide.",
                id="diff-content",
            )
        )


def run() -> None:
    """Entry point for the TUI application."""
    import argparse
    import sys

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

    # Validate file exists before setting up logging (so error is visible to user)
    target_path = Path(args.markdown_document).expanduser().resolve()
    if not target_path.exists():
        print(f"Error: File not found: {target_path}", file=sys.stderr)
        print("Please check that the file exists and the path is correct.", file=sys.stderr)
        sys.exit(1)
    if not target_path.is_file():
        print(f"Error: Path is not a file: {target_path}", file=sys.stderr)
        sys.exit(1)

    # Setup logging (TUI mode - only log to file, not to stdout)
    log_file = setup_logging(tui_mode=True)
    logger.info(f"TUI session started. Log file: {log_file}")

    # Setup environment and target
    setup_environment()
    context = load_and_validate_target(args.markdown_document)

    # Get style pages
    style_pages = get_style_guides(skip_through=args.skip_through, final_pass=args.final_pass)

    # Initialize Controller
    seen_edits: set[tuple[str, str]] = set()
    controller = ReviewController(
        context.target_path,
        style_pages,
        seen_edits,
        notebook_handler=context.notebook_handler,
    )

    # Run the TUI
    app = AutoDocsEditorTUI(controller)
    app.run()

    # Final sync back to notebook if needed
    if context.notebook_handler:
        logger.info("Final sync: Syncing changes back to notebook...")
        try:
            context.notebook_handler.sync_back()
            logger.success(f"Successfully updated notebook: {context.original_target}")
            logger.info(f"Paired Markdown preserved at: {context.target_path}")
        except RuntimeError as e:
            logger.error(f"Failed to sync back to notebook: {e}")
            logger.warning(f"Markdown edits are preserved in: {context.target_path}")
            sys.exit(1)


if __name__ == "__main__":
    run()
