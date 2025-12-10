from __future__ import annotations

import difflib

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea


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
