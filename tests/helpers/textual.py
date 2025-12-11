"""Utilities for interacting with Textual's Pilot in tests."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from textual.app import ScreenStackError


async def drain_pilot(pilot, timeout: float = 1.0) -> None:
    """Wait for Textual's message queue (and any BaseScreen workers) to settle."""
    await pilot.pause()

    # Handle ScreenStackError if checking screen property when stack is empty
    try:
        screen = getattr(pilot.app, "screen", None)
    except ScreenStackError:
        screen = None

    wait_for_workers = getattr(screen, "wait_for_workers_idle", None)
    if callable(wait_for_workers):
        try:
            await wait_for_workers(timeout=timeout)
        except TimeoutError:
            pass


async def wait_for_condition(
    pilot,
    predicate: Callable[[], bool],
    timeout: float = 1.0,
) -> None:
    """Poll for a condition without sprinkling raw pilot.pause() loops everywhere."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await drain_pilot(pilot, timeout=max(timeout, 0.5))
    raise AssertionError("Timed out waiting for condition")


async def push_screen_and_drain(app: Any, pilot, screen: Any) -> None:
    """Push a screen and wait for Textual to process resulting messages."""
    app.push_screen(screen)
    await drain_pilot(pilot)


async def press_and_drain(pilot, *keys: str) -> None:
    """Press a key combination and wait for any resulting UI work to finish."""
    await pilot.press(*keys)
    await drain_pilot(pilot)


async def focus_and_drain(widget: Any, pilot) -> None:
    """Focus a widget and wait for focus/worker side effects to settle."""
    widget.focus()
    await drain_pilot(pilot)


async def wait_for_screen_workers(screen: Any, pilot, timeout: float = 5.0) -> None:
    """Wait for all screen workers to complete.

    This is useful for screens that load data in the background.
    """
    wait_for_workers = getattr(screen, "wait_for_workers_idle", None)
    if callable(wait_for_workers):
        try:
            await wait_for_workers(timeout=timeout)
        except TimeoutError:
            pass
    await drain_pilot(pilot, timeout=timeout)


def _screen_stack_depth(app: Any) -> int:
    stack = getattr(app, "_screen_stack", None)
    try:
        return len(stack) if stack is not None else 0
    except TypeError:
        return 0


async def reset_screen_stack(app: Any, pilot, target_depth: int = 1) -> None:
    """Pop screens until stack depth reaches the target depth (default root).

    Falls back to manually trimming `_screen_stack` when tests monkeypatch
    `app.pop_screen` or `app.push_screen` to a no-op (common in button
    interaction tests). This keeps worker teardown deterministic even when
    navigation helpers are stubbed out.
    """

    stack = getattr(app, "_screen_stack", None)
    if stack is None:
        await drain_pilot(pilot)
        return

    while True:
        depth = len(stack)
        if depth <= target_depth:
            break

        depth_before_pop = depth
        pop_method = getattr(app, "pop_screen", None)
        if callable(pop_method):
            try:
                result = pop_method()
                if inspect.isawaitable(result):
                    await result
            except ScreenStackError:
                break
        # If pop_screen is mocked (or failed), trim manually to avoid infinite loops
        if len(stack) >= depth_before_pop:
            if depth_before_pop <= 1:
                break
            stack.pop()
        await drain_pilot(pilot)

    await drain_pilot(pilot)


@asynccontextmanager
async def screen_session(app: Any, pilot, screen: Any):
    """Push a screen for the duration of the context and guarantee cleanup.

    This helper ensures every temporary screen gets popped (and its workers are
    allowed to shut down) even when assertions fail mid-test, which prevents
    Textual worker leaks from crashing parallel pytest workers.
    """

    initial_depth = _screen_stack_depth(app)
    await push_screen_and_drain(app, pilot, screen)
    try:
        yield
    finally:
        await reset_screen_stack(app, pilot, target_depth=initial_depth)
