"""Tests for BackgroundTasks parameter safety in conversations route."""

import inspect

import pytest


class TestBackgroundTasksParameter:
    """Verify send_message does not use a mutable default for BackgroundTasks."""

    def test_no_mutable_default_for_background_tasks(self) -> None:
        """BackgroundTasks parameter should not have a default value.

        A mutable default like `BackgroundTasks()` would be shared across requests,
        causing background tasks to leak between requests. FastAPI injects
        BackgroundTasks automatically when no default is set.
        """
        from src.api.routes.conversations import send_message

        sig = inspect.signature(send_message)
        param = sig.parameters.get("background_tasks")

        assert param is not None, "send_message should have a background_tasks parameter"
        assert param.default is inspect.Parameter.empty, (
            "background_tasks should not have a default value. "
            "FastAPI injects BackgroundTasks automatically. "
            f"Found default: {param.default}"
        )

    def test_background_tasks_type_annotation(self) -> None:
        """BackgroundTasks parameter should be properly annotated."""
        from fastapi import BackgroundTasks
        from src.api.routes.conversations import send_message

        sig = inspect.signature(send_message)
        param = sig.parameters.get("background_tasks")

        assert param is not None
        assert param.annotation is BackgroundTasks
