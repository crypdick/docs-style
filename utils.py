from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from loguru import logger

from settings import LOGS_DIR

T = TypeVar("T")

CURRENT_RUN_DIR: Path | None = None


async def read_text_async(path: Path, encoding: str = "utf-8") -> str:
    """Read text from a file asynchronously."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_text, encoding)


async def write_text_async(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to a file asynchronously."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: path.write_text(content, encoding=encoding))


def setup_logging(tui_mode: bool = False) -> Path:
    """Configure logging with Loguru to write *all* console output to a file in logs/.

    Args:
        tui_mode: If True, only log to file (not to stdout) to avoid interfering with TUI display.
    """
    global CURRENT_RUN_DIR

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    run_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    CURRENT_RUN_DIR = LOGS_DIR / run_timestamp
    CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

    log_path = CURRENT_RUN_DIR / "session.log"

    # Configure Loguru sinks: console (unless in TUI mode) + file.
    logger.remove()

    # Only add stdout sink in CLI mode (not in TUI mode)
    if not tui_mode:
        logger.add(
            sys.stdout,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} {level}: {message}",
            colorize=True,
        )

    # Always add file sink
    logger.add(
        log_path,
        level="INFO",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} {level}: {message}",
        colorize=False,  # Don't colorize file output
    )

    return log_path


def get_langfuse_handler():
    """Initialize Langfuse callback handler if credentials are present."""
    if os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"):
        logger.info("Langfuse credentials found. Initializing tracing.")
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()

    logger.info("Langfuse credentials not found. Tracing disabled.")
    return None
