import contextlib

import pytest
import pytest_asyncio
from loguru import logger

from docs_style.tui import AutoDocsEditorTUI
from tests.helpers.textual import reset_screen_stack


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable loguru logging during tests."""
    logger.remove()


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set dummy environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "dummy")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "dummy")


@pytest.fixture(autouse=True)
def disable_langfuse(monkeypatch):
    """Disable Langfuse by patching imports or ensuring it initializes as None/Mock."""
    # Since Langfuse is imported at module level in core.py, we might need to patch it before import
    # But usually modules are imported when tests run.
    # We can patch the class if it's already imported.
    pass


# NOTE: No default `controller` fixture is provided here.
# Tests using the `app` fixture must define their own `controller` fixture.
# This prevents accidental use of MagicMock controllers which can mask bugs
# (e.g., MagicMock.is_notebook is truthy, arithmetic on MagicMock returns MagicMock).


@pytest_asyncio.fixture
async def app(controller):
    """Provide an AutoDocsEditorTUI instance for UI testing.

    This fixture ensures proper cleanup of the app instance to prevent
    state leakage between tests.

    IMPORTANT: Tests using this fixture must define their own `controller` fixture
    that provides a real ReviewController instance.
    """
    app_instance = AutoDocsEditorTUI(controller)

    # Patch run_test to ensure proper draining at the end of the test context
    # This prevents "worker not properly terminated" errors in parallel tests
    orig_run_test = app_instance.run_test

    @contextlib.asynccontextmanager
    async def run_test_patched(*args, **kwargs):
        async with orig_run_test(*args, **kwargs) as pilot:
            try:
                yield pilot
            finally:
                # Ensure we unwind to the root screen and drain pending work
                await reset_screen_stack(app_instance, pilot)

    app_instance.run_test = run_test_patched

    yield app_instance

    # Cleanup: ensure all background workers and tasks are cancelled
    try:
        if hasattr(app_instance, "_workers"):
            for worker in list(app_instance._workers):
                if not worker.is_cancelled:
                    worker.cancel()

        # Give async cleanup time to complete
        import asyncio

        await asyncio.sleep(0.05)
    except (AttributeError, RuntimeError):
        pass
