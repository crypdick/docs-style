#!/usr/bin/env python3
"""Main entry point for auto_docs_editor.

This script allows you to launch either the TUI (interactive) or CLI (automatic) mode.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Main entry point that dispatches to TUI or CLI mode."""
    if len(sys.argv) < 2:
        print(
            "Auto Docs Editor - Apply Google Style Guide to markdown documents and Jupyter notebooks"
        )
        print()
        print("Usage:")
        print("  python main.py tui <document> [options]   # Interactive TUI mode")
        print("  python main.py cli <document> [options]   # Automatic CLI mode")
        print()
        print("Supported formats:")
        print("  - Markdown files (.md)")
        print("  - Jupyter notebooks (.ipynb) - converted via Jupytext")
        print()
        print("Or use the installed commands:")
        print("  auto-docs-tui <document> [options]")
        print("  auto-docs-edit <document> [options]")
        print()
        print("Options:")
        print("  --skip-through STYLE_FILE  Skip style guides up to and including this file")
        print("  --final-pass               Process only final-pass style guides (marked with +)")
        print("  --yolo                     (CLI only) Auto-accept all edits without review")
        print()
        print("Examples:")
        print("  python main.py tui docs/article.md")
        print("  python main.py tui notebooks/tutorial.ipynb")
        print("  python main.py cli --yolo docs/article.md")
        print("  python main.py tui --final-pass docs/article.md")
        sys.exit(0)

    mode = sys.argv[1].lower()

    if mode in ("tui", "interactive", "ui"):
        # Remove the mode argument and launch TUI
        sys.argv.pop(1)
        from auto_docs_editor.tui import run

        run()
    elif mode in ("cli", "auto", "automatic"):
        # Remove the mode argument and launch CLI
        sys.argv.pop(1)
        from auto_docs_editor.cli import main as cli_main

        cli_main()
    else:
        print(f"Error: Unknown mode '{mode}'")
        print("Valid modes: tui, cli")
        print("Run 'python main.py' for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
