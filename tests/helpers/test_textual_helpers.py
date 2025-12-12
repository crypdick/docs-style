"""Tests for shared Textual helper utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from tests.helpers.textual import screen_session


@dataclass
class FakeApp:
    """Minimal app stub that mimics Textual's screen stack behavior."""

    _screen_stack: list[Any] = field(default_factory=lambda: ["root"])

    def push_screen(self, screen: Any) -> None:
        self._screen_stack.append(screen)

    async def pop_screen(self) -> None:
        if len(self._screen_stack) <= 1:
            msg = "Cannot pop the root screen"
            raise RuntimeError(msg)
        self._screen_stack.pop()


class FakePilot:
    """Pilot stub for testing."""

    def __init__(self, app):
        self.app = app

    async def pause(self) -> None:
        pass


@pytest.mark.asyncio
async def test_screen_session_pushes_and_cleans_up() -> None:
    """screen_session should push, then pop screens and drain the pilot."""

    app = FakeApp()
    pilot = FakePilot(app)

    with patch("tests.helpers.textual.drain_pilot", new_callable=AsyncMock) as drain_mock:
        async with screen_session(app, pilot, "daily_dash"):
            assert app._screen_stack[-1] == "daily_dash"
            assert len(app._screen_stack) == 2

        # push_screen_and_drain + pop cleanup + final drain => three calls
        assert drain_mock.await_count == 3

    assert app._screen_stack == ["root"]


@pytest.mark.asyncio
async def test_screen_session_handles_nested_contexts() -> None:
    """Nested screen contexts should restore stack depth correctly."""

    app = FakeApp()
    pilot = FakePilot(app)

    with patch("tests.helpers.textual.drain_pilot", new_callable=AsyncMock) as drain_mock:
        async with screen_session(app, pilot, "daily_dash"):
            assert app._screen_stack == ["root", "daily_dash"]

            async with screen_session(app, pilot, "settings"):
                assert app._screen_stack == ["root", "daily_dash", "settings"]

            # After inner context exits we should still be on the outer screen
            assert app._screen_stack == ["root", "daily_dash"]

        assert app._screen_stack == ["root"]
        assert drain_mock.await_count >= 1


@pytest.mark.asyncio
async def test_screen_session_handles_mocked_pop_screen() -> None:
    """Cleanup should fall back to manual stack pops when pop_screen is mocked."""

    app = FakeApp()
    pilot = FakePilot(app)

    async def noop_pop() -> None:
        return None

    app.pop_screen = noop_pop

    with patch("tests.helpers.textual.drain_pilot", new_callable=AsyncMock) as drain_mock:
        async with screen_session(app, pilot, "daily_dash"):
            assert app._screen_stack == ["root", "daily_dash"]

        assert app._screen_stack == ["root"]
        assert drain_mock.await_count >= 1


@pytest.mark.asyncio
async def test_screen_session_cleans_up_on_error() -> None:
    """screen_session must pop the screen even if the block raises."""

    app = FakeApp()
    pilot = FakePilot(app)

    with patch("tests.helpers.textual.drain_pilot", new_callable=AsyncMock):
        with pytest.raises(RuntimeError):
            async with screen_session(app, pilot, "settings"):
                raise RuntimeError("boom")

    # screen stack is restored despite the error
    assert app._screen_stack == ["root"]
