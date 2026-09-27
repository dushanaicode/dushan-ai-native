import asyncio

import pytest

from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.lifecycle import post_construct_hook, pre_destroy_hook
from framework.starter_di.definitions.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit


def exception_chain(error):
    """只遍历显式原因和错误组，避免隐式上下文掩盖被覆盖的原因链。"""
    yield error
    if error.__cause__ is not None:
        yield from exception_chain(error.__cause__)
    if isinstance(error, BaseExceptionGroup):
        for item in error.exceptions:
            yield from exception_chain(item)


@pytest.mark.parametrize("descriptor", [staticmethod, classmethod])
@pytest.mark.parametrize("hook", [post_construct_hook, pre_destroy_hook])
def test_starter_di_lifecycle_decorator_rejects_descriptor_as_inner_decorator(descriptor, hook):
    def lifecycle(self):
        pass

    with pytest.raises(TypeError, match="生命周期标记只能用于实例方法"):
        hook(descriptor(lifecycle))


@pytest.mark.parametrize("concurrent_shutdown", [False, True])
@pytest.mark.parametrize("cancel_at", [None, "initialize", "cleanup"])
async def test_starter_di_application_rollback_preserves_causes_and_cancellation(
    contexts, concurrent_shutdown, cancel_at
):
    initialized, destroying, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    destroyed = []
    original = RuntimeError("initialization failed")
    cleanup_error = ValueError("destruction failed")

    @service
    class Resource:
        async def post_construct(self):
            initialized.set()
            if cancel_at == "initialize":
                await asyncio.Event().wait()
            raise original

        async def pre_destroy(self):
            destroyed.append(True)
            destroying.set()
            await release.wait()
            raise cleanup_error

    current = contexts([Resource])
    starting = asyncio.create_task(current.startup())
    closing = None
    try:
        await asyncio.wait_for(initialized.wait(), 1)
        if cancel_at == "initialize":
            starting.cancel("startup cancelled")
        await asyncio.wait_for(destroying.wait(), 1)
        shared = current.container._shutdown_task
        assert shared is not None and not shared.done()
        if concurrent_shutdown:
            closing = asyncio.create_task(current.shutdown())
            await asyncio.sleep(0)
        if cancel_at == "cleanup":
            starting.cancel("startup cancelled")
            await asyncio.sleep(0)
            assert not starting.done() and not shared.done()
        release.set()
        expected = asyncio.CancelledError if cancel_at else DiException
        with pytest.raises(expected) as caught:
            await asyncio.wait_for(starting, 1)
        causes = tuple(exception_chain(caught.value))
        assert cleanup_error in causes
        if cancel_at != "initialize":
            assert original in causes
        if cancel_at:
            assert caught.value.args == ("startup cancelled",)
        if closing is not None:
            with pytest.raises(BaseExceptionGroup):
                await closing
        assert current.container._shutdown_task is shared and destroyed == [True]
        assert current.state is ApplicationStateEnum.CLOSED
        assert current.container.state is ContainerStateEnum.CLOSED
    finally:
        release.set()
        await asyncio.gather(
            starting, *(() if closing is None else (closing,)), return_exceptions=True
        )
