from __future__ import annotations

import concurrent.futures
import itertools
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

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


class Spinner:
    """A simple terminal spinner."""

    def __init__(self, message: str, delay: float = 0.1) -> None:
        self.message = message
        self.delay = delay
        self.spinner = itertools.cycle("|/-\\")
        self.last_tick = 0.0

    def tick(self) -> None:
        now = time.time()
        if now - self.last_tick >= self.delay:
            sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            self.last_tick = now

    def clear(self) -> None:
        sys.stdout.write(f"\r{' ' * (len(self.message) + 5)}\r")
        sys.stdout.flush()


def check_cancellation(fd: int | None) -> bool:
    """Check if ESC was pressed (non-blocking)."""
    if os.name == "nt":
        import msvcrt  # type: ignore

        if msvcrt.kbhit() and msvcrt.getch() == b"\x1b":
            return True
    elif fd is not None:
        import os as _os
        import select

        ready, _, _ = select.select([fd], [], [], 0)
        if ready and _os.read(fd, 1) == b"\x1b":
            return True
    return False


def setup_input_mode() -> tuple[int | None, list | None]:
    """Configure terminal for single-character input (ESC detection)."""
    fd = None
    old_termios = None
    if os.name != "nt" and sys.stdin.isatty():
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_termios = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    return fd, old_termios


def restore_input_mode(fd: int | None, old_termios: list | None) -> None:
    """Restore terminal settings."""
    if fd is not None and old_termios is not None:
        import termios

        termios.tcsetattr(fd, termios.TCSADRAIN, old_termios)


def run_with_spinner(fn: Callable[[], T], message: str) -> T | None:
    """Execute *fn* in a worker thread while showing a spinner.

    Returns the function's result, or ``None`` if the user presses ESC to
    cancel while waiting. The worker thread continues running in the
    background, but its result is discarded.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)

    fd, old_termios = setup_input_mode()
    spinner = Spinner(message)

    try:
        while not future.done():
            spinner.tick()

            if check_cancellation(fd):
                return None

            time.sleep(0.05)

        return future.result()
    finally:
        spinner.clear()
        restore_input_mode(fd, old_termios)
        executor.shutdown(wait=False)
