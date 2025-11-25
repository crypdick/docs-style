from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from loguru import logger

from settings import LOGS_DIR

T = TypeVar("T")

CURRENT_RUN_DIR: Path | None = None


def setup_logging() -> Path:
    """Configure logging with Loguru to write *all* console output to a file in logs/."""
    global CURRENT_RUN_DIR

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    CURRENT_RUN_DIR = LOGS_DIR / run_timestamp
    CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

    log_path = CURRENT_RUN_DIR / "session.log"

    # Configure Loguru sinks: console + file.
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} {level}: {message}",
        colorize=True,
    )
    logger.add(
        log_path,
        level="INFO",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} {level}: {message}",
        colorize=False,  # Don't colorize file output
    )

    return log_path


def log_incident(
    guide_path: Path,
    target_doc: Path,
    diff_text: str,
    missed_snippets: list[str],
) -> None:
    """Write an incident log file containing the problematic diff and context."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{timestamp}_{guide_path.stem}.log"
    run_dir = CURRENT_RUN_DIR if CURRENT_RUN_DIR is not None else LOGS_DIR
    incident_path = run_dir / fname

    missed_section = "\n".join(f"- {s}" for s in missed_snippets) if missed_snippets else "<none>"

    content = (
        f"Guide: {guide_path.name}\n"
        f"Target doc: {target_doc}\n"
        f"Missed snippets: {missed_section}\n"
        f"--- DIFF START ---\n{diff_text}\n--- DIFF END ---\n"
    )

    incident_path.write_text(content, encoding="utf-8")
