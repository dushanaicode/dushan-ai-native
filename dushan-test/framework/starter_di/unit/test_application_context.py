import asyncio
import threading
from contextvars import ContextVar

import pytest

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.context.di_task_runner import DiTaskRunner
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit


async def test_inject_and_lookup_share_app_singletons_and_restore_nested_context(contexts):
    @service
    class Repository:
        pass

    @service
    class Consumer:
        repository: Repository = Inject()

    first, second = contexts([Repository, Consumer]), contexts([Repository, Consumer])
    await first.startup()
    await second.startup()
    with pytest.raises(DiException):
        with first.execution():
            pass
    first.mark_ready()
    second.mark_ready()
    with pytest.raises(DiException) as absent:
        get_bean(Repository)
    assert absent.value.error_code == DiErrorCodes.CONTEXT_MISSING
    with first.execution():
        a = get_bean(Repository)
        consumer = get_bean(Consumer)
        assert consumer.repository is a
        with second.execution():
            assert get_bean(Repository) is not a
            with pytest.raises(DiException) as mismatch:
                _ = consumer.repository
            assert mismatch.value.error_code == DiErrorCodes.CONTEXT_MISMATCH
        assert get_bean(Repository) is a
    await first.shutdown()
    with second.execution():
        assert get_bean(Repository) is not a
    await second.shutdown()


async def test_disabled_lookup_and_metrics_do_not_disable_injection(contexts):
    @service
    class Repository:
        pass

    @service
    class Consumer:
        repository: Repository = Inject()

    current = contexts([Repository, Consumer], lookup_enabled=False, metrics_enabled=False)
    await current.startup()
    current.mark_ready()
    with current.execution():
        assert current.container.get(Consumer).repository is current.container.get(Repository)
        with pytest.raises(DiException) as disabled:
            get_bean(Repository)
        assert disabled.value.error_code == DiErrorCodes.LOOKUP_DISABLED
    assert current.container.get_statistics()["resolutions"] == 0
    await current.shutdown()


async def test_unmanaged_child_cannot_use_an_expired_parent_execution(contexts):
    current = contexts()
    await current.startup()
    current.mark_ready()
    release = asyncio.Event()

    async def later():
        await release.wait()
        return get_bean(DiContainer)

    with current.execution():
        task = asyncio.create_task(later())
    release.set()
    with pytest.raises(DiException) as expired:
        await task
    assert expired.value.error_code == DiErrorCodes.CONTEXT_EXPIRED
    await current.shutdown()


async def test_shutdown_waits_for_business_after_lookup_and_preserves_cancellation(contexts):
    started, release, closed = asyncio.Event(), asyncio.Event(), []

    @service
    class Resource:
        async def pre_destroy(self):
            closed.append(True)

    current = contexts([Resource])
    await current.startup()
    current.mark_ready()

    async def business():
        resource = get_bean(Resource)
        started.set()
        await release.wait()
        assert get_bean(Resource) is resource and not closed

    task = current.tasks.create_task(business)
    await started.wait()
    closing = asyncio.create_task(current.shutdown())
    await asyncio.sleep(0.01)
    assert not closed and current.state is ApplicationStateEnum.DRAINING
    with pytest.raises(DiException):
        with current.execution():
            pass
    closing.cancel("first")
    await asyncio.sleep(0)
    closing.cancel("second")
    release.set()
    await task
    with pytest.raises(asyncio.CancelledError):
        await closing
    assert closed == [True] and current.state is ApplicationStateEnum.CLOSED


async def test_drain_timeout_cancels_owned_tasks_and_closes_only_after_finally(contexts):
    started, finished, closed = asyncio.Event(), [], []

    @service
    class Resource:
        def pre_destroy(self):
            assert finished == [True]
            closed.append(True)

    current = contexts([Resource], drain_timeout_seconds=0.01)
    await current.startup()
    current.mark_ready()

    async def business():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            assert get_bean(Resource) is not None
            finished.append(True)

    task = current.tasks.create_task(business)
    await started.wait()
    with pytest.raises(BaseExceptionGroup) as error:
        await current.shutdown()
    assert any(item.error_code == DiErrorCodes.DRAIN_TIMEOUT for item in error.value.exceptions)
    assert task.cancelled() and closed == [True]
    assert current.get_statistics()["executions"] == 0


async def test_sync_worker_is_admitted_and_is_not_destroyed_by_timeout(contexts):
    entered, release = threading.Event(), threading.Event()
    current = contexts(drain_timeout_seconds=0.01)
    await current.startup()
    current.mark_ready()

    def callback():
        assert get_bean(DiContainer) is current.container
        entered.set()
        assert release.wait(2)
        assert get_bean(DiContainer) is current.container

    worker = asyncio.create_task(asyncio.to_thread(current.tasks.run_sync, callback))
    assert await asyncio.to_thread(entered.wait, 1)
    closing = asyncio.create_task(current.shutdown())
    await asyncio.sleep(0.04)
    assert not closing.done() and current.container.state is ContainerStateEnum.READY
    release.set()
    await worker
    with pytest.raises(BaseExceptionGroup):
        await closing
    assert current.state is ApplicationStateEnum.CLOSED


async def test_startup_tasks_wait_for_resource_ready_and_cancel_before_first_run(contexts):
    events = []

    @service
    class Resource:
        tasks: DiTaskRunner = Inject()

        async def post_construct(self):
            async def background():
                events.append(get_bean(Resource))

            self.task = self.tasks.create_task(background)

    current = contexts([Resource])
    await current.startup()
    await asyncio.sleep(0)
    assert events == []
    current.mark_ready()
    await asyncio.sleep(0)
    await current.drain()
    assert len(events) == 1
    await current.shutdown()
    second = contexts([Resource])
    await second.startup()
    await second.shutdown()
    assert len(events) == 1 and second.get_statistics()["executions"] == 0


async def test_task_error_and_reentrant_shutdown_are_visible(contexts):
    current = contexts()
    await current.startup()
    current.mark_ready()
    with current.execution():
        with pytest.raises(DiException, match="不能等待"):
            await current.shutdown()

    async def broken():
        raise ValueError("background failure")

    task = current.tasks.create_task(broken)
    with pytest.raises(ValueError):
        await task
    with pytest.raises(BaseExceptionGroup) as caught:
        await current.shutdown()
    assert caught.value.exceptions[0].error_code == DiErrorCodes.TASK_FAILED
    assert isinstance(caught.value.exceptions[0].__cause__, ValueError)
    assert current.state is ApplicationStateEnum.CLOSED


async def test_detached_tasks_do_not_inherit_request_contextvars(contexts):
    principal = ContextVar("test_principal", default=None)
    current = contexts()
    await current.startup()
    current.mark_ready()

    async def callback():
        assert get_bean(ApplicationContext) is current
        return principal.get()

    token = principal.set("request principal")
    try:
        assert await current.tasks.run(callback) == "request principal"
        assert await current.tasks.create_task(callback) is None
    finally:
        principal.reset(token)
    await current.shutdown()


async def test_awaited_lifecycle_children_can_use_ready_injected_dependencies(contexts):
    events = []

    @service
    class Dependency:
        pass

    @service
    class Resource:
        dependency: Dependency = Inject()

        async def check_dependency(self):
            assert self.dependency is get_bean(Dependency)

        async def post_construct(self):
            await asyncio.gather(self.check_dependency(), self.check_dependency())
            events.append("initialized")

        async def pre_destroy(self):
            await asyncio.gather(self.check_dependency(), self.check_dependency())
            events.append("destroyed")

    current = contexts([Dependency, Resource])
    await current.startup()
    current.mark_ready()
    await current.shutdown()
    assert events == ["initialized", "destroyed"]


async def test_draining_allows_nested_continuation_but_rejects_new_background_work(contexts):
    current = contexts()
    await current.startup()
    current.mark_ready()
    entered, release = asyncio.Event(), asyncio.Event()

    async def continuation():
        assert get_bean(DiContainer) is current.container

    async def business():
        entered.set()
        await release.wait()
        await current.tasks.run(continuation)
        with pytest.raises(DiException):
            current.tasks.create_task(continuation)

    task = current.tasks.create_task(business)
    await entered.wait()
    closing = asyncio.create_task(current.shutdown())
    await asyncio.sleep(0.01)
    assert current.state is ApplicationStateEnum.DRAINING
    release.set()
    await task
    await closing
    assert current.get_statistics()["executions"] == 0
