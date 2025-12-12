import contextlib
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from loguru import logger

from auto_docs_editor.tui import AutoDocsEditorTUI
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


@pytest.fixture
def controller():
    """Provide a default mock controller."""
    controller = MagicMock()
    # Mock necessary attributes of controller to avoid crashes during __init__ or on_mount
    controller.is_finished = False
    controller.current_guide_path = None
    controller.progress_str = "0/0"
    return controller


@pytest_asyncio.fixture
async def app(controller):
    """Provide an AutoDocsEditorTUI instance for UI testing.

    This fixture ensures proper cleanup of the app instance to prevent
    state leakage between tests.
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
