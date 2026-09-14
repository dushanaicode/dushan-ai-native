import asyncio

import pytest
from loguru import logger

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.exception.di_exception import DiException


async def test_background_tasks_are_owned_by_the_application_and_closed(contexts):
    first, second = contexts(), contexts()
    await first.startup()
    await second.startup()
    first.mark_ready()
    second.mark_ready()
    started, closed = asyncio.Event(), asyncio.Event()

    async def background():
        assert ApplicationContext.current() is first
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            closed.set()

    try:
        task = first.tasks.create_task(background)
        await started.wait()
        await second.shutdown()
        assert not task.done()
        first.tasks.cancel_pending()
        await first.shutdown()
        assert task.cancelled() and closed.is_set()
        assert first.get_statistics()["executions"] == 0
        with pytest.raises(DiException):
            first.tasks.create_task(background)
    finally:
        first.tasks.cancel_pending()
        second.tasks.cancel_pending()
        await first.shutdown()
        await second.shutdown()


async def test_background_failure_is_reported_by_its_application_after_redaction(contexts):
    application = contexts()
    await application.startup()
    application.mark_ready()
    messages = []
    sink = logger.add(lambda message: messages.append(str(message)))

    async def fail():
        raise ValueError("password=private-value")

    try:
        task = application.tasks.create_task(fail, name="owned-failure")
        await asyncio.gather(task, return_exceptions=True)
        with pytest.raises(BaseExceptionGroup):
            await application.shutdown()
        assert application.get_statistics()["task_failures"] == 1
        assert application.tasks.active_count == 0
    finally:
        logger.remove(sink)
    output = "".join(messages)
    assert "应用后台任务失败" in output and "private-value" not in output
