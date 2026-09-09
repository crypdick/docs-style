"""Argument parsing for the interactive editor."""

import argparse

from settings import FINAL_PASS_MARKER


def parse_arguments() -> argparse.Namespace:
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
    return parser.parse_args()
