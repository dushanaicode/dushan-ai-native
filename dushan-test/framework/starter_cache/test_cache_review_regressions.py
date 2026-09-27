import asyncio
from types import SimpleNamespace

from framework.starter_cache.core.cache_generation_publisher import CacheGenerationPublisher
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.core.cache_resource_snapshot import CacheResourceSnapshot
from framework.starter_cache.core.cache_serializer import CacheSerializer
from framework.starter_cache.decorators.key_builder import KeyBuilder
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes
from framework.starter_cache.definitions.enums.cache_generation_state_enum import (
    CacheGenerationStateEnum,
)
from framework.starter_cache.definitions.enums.cache_lifecycle_phase_enum import (
    CacheLifecyclePhaseEnum,
)
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.lock.distributed_lock import DistributedLock
from framework.starter_cache.model.cache_generation_state import CacheGenerationState


def check(name: str, ok: bool, detail: str = "") -> None:
    assert ok, f"{name}: {detail}"


async def _value(n):
    return n


async def _raise(error):
    raise error


class FakeCoordinator:
    def __init__(self, finalize_error=None, finalize_gate=None):
        self.finalize_calls = 0
        self.finalize_error = finalize_error
        self.finalize_gate = finalize_gate
        self.entered_finalize = asyncio.Event()

    @staticmethod
    def build_generation_key(cache_key):
        return "cache_generation:prefix:demo"

    @staticmethod
    async def begin(client, generation_key):
        return object()

    async def finalize(self, client, generation):
        self.entered_finalize.set()
        if self.finalize_gate is not None:
            await self.finalize_gate
        self.finalize_calls += 1
        if self.finalize_error is not None:
            raise self.finalize_error


class HandlerStub:
    pass


def make_invalidation(coordinator):
    stub = HandlerStub()
    stub._coordinator = coordinator
    return CacheHandler._run_invalidation.__get__(stub, HandlerStub)


async def test_invalidation_success():
    coordinator = FakeCoordinator()
    run = make_invalidation(coordinator)
    deleted = await run(None, None, lambda: _value(7))
    check(
        "A1 正常路径返回删除数且 finalize 一次",
        deleted == 7 and coordinator.finalize_calls == 1,
        f"deleted={deleted} finalize={coordinator.finalize_calls}",
    )


async def test_invalidation_operation_failed():
    coordinator = FakeCoordinator()
    run = make_invalidation(coordinator)
    boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="删除失败")
    try:
        await run(None, None, lambda: _raise(boom))
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "A2 删除失败仍 finalize，主异常原样抛出",
        raised is boom and coordinator.finalize_calls == 1,
        f"raised={type(raised).__name__} finalize={coordinator.finalize_calls}",
    )


async def test_invalidation_cancelled_during_operation():
    coordinator = FakeCoordinator()
    run = make_invalidation(coordinator)
    started = asyncio.Event()

    async def blocking():
        started.set()
        await asyncio.Event().wait()
        return 0

    task = asyncio.create_task(run(None, None, blocking))
    await started.wait()
    task.cancel()
    try:
        await task
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "A3 删除期间被取消仍 finalize，CancelledError 传播",
        isinstance(raised, asyncio.CancelledError) and coordinator.finalize_calls == 1,
        f"raised={type(raised).__name__} finalize={coordinator.finalize_calls}",
    )
    check("A3b 任务终态为 cancelled", task.cancelled(), f"cancelled={task.cancelled()}")


async def test_invalidation_cancelled_during_finalize():
    gate = asyncio.get_running_loop().create_future()
    coordinator = FakeCoordinator(finalize_gate=gate)
    run = make_invalidation(coordinator)
    task = asyncio.create_task(run(None, None, lambda: _value(3)))
    await coordinator.entered_finalize.wait()
    task.cancel()
    await asyncio.sleep(0)
    still_running = not task.done()
    gate.set_result(None)
    try:
        await task
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "A4 finalize 期间被取消：等到终态后才传播取消",
        still_running
        and isinstance(raised, asyncio.CancelledError)
        and coordinator.finalize_calls == 1,
        f"still_running={still_running} raised={type(raised).__name__} "
        f"finalize={coordinator.finalize_calls}",
    )


async def test_invalidation_finalize_failed():
    boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="finalize 失败")
    coordinator = FakeCoordinator(finalize_error=boom)
    run = make_invalidation(coordinator)
    try:
        await run(None, None, lambda: _value(1))
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "A5 finalize 失败原样上抛（保留缓存错误码，不包成异常组）",
        raised is boom,
        f"raised={raised!r}",
    )


class FakeClient:
    def __init__(self, error=None):
        self.error = error
        self.closed = False

    async def aclose(self):
        if self.error is not None:
            raise self.error
        self.closed = True


class FakePool:
    def __init__(self, error=None):
        self.error = error
        self.closed = False

    async def disconnect(self, inuse_connections=True):
        if self.error is not None:
            raise self.error
        self.closed = True


def make_manager(clients, pools):
    manager = CacheManager()
    manager._phase = CacheLifecyclePhaseEnum.READY
    manager._active = CacheResourceSnapshot(clients=clients, pools=pools)
    return manager


async def test_close_cancel_with_other_error():
    client = FakeClient(asyncio.CancelledError())
    pool = FakePool(RuntimeError("pool 关闭失败"))
    manager = make_manager({"default": client}, {"default": pool})
    try:
        await manager.close()
    except BaseException as error:
        raised = error
    else:
        raised = None
    cause = getattr(raised, "__cause__", None)
    ok = (
        isinstance(raised, asyncio.CancelledError)
        and isinstance(cause, BaseExceptionGroup)
        and len(cause.exceptions) == 1
        and manager.phase is CacheLifecyclePhaseEnum.CLOSE_FAILED
        and set(manager._pending_close.clients) == {"default"}
        and set(manager._pending_close.pools) == {"default"}
    )
    check(
        "B1 关闭期间取消 + 其他失败：抛 CancelledError，失败经异常链保留",
        ok,
        f"raised={type(raised).__name__} cause={type(cause).__name__} phase={manager.phase.code}",
    )


async def test_close_single_error_unchanged():
    boom = RuntimeError("client 关闭失败")
    client = FakeClient(boom)
    pool = FakePool()
    manager = make_manager({"default": client}, {"default": pool})
    try:
        await manager.close()
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "B2 单个关闭失败仍原样抛出（行为不变）",
        raised is boom and manager.phase is CacheLifecyclePhaseEnum.CLOSE_FAILED and pool.closed,
        f"raised={type(raised).__name__} phase={manager.phase.code}",
    )


async def test_close_clean():
    client = FakeClient()
    pool = FakePool()
    manager = make_manager({"default": client}, {"default": pool})
    await manager.close()
    check(
        "B3 正常关闭进入 STOPPED 且无残留",
        manager.phase is CacheLifecyclePhaseEnum.STOPPED
        and manager._pending_close.is_empty
        and client.closed
        and pool.closed,
        f"phase={manager.phase.code}",
    )


def test_key_builder():
    def handler(self, x: str, y: int) -> None: ...

    signature = KeyBuilder.get_signature(handler)
    identifier = KeyBuilder.build_identifier(
        "a:{{x}}:b:{{y}}", handler, signature, (None, "{{y}}", 2), {}
    )
    check(
        "C1 参数值里的 {{y}} 不再被二次替换",
        identifier == "a:{{y}}:b:2",
        f"identifier={identifier}",
    )

    def by_permission(self, permission: str) -> None: ...

    signature = KeyBuilder.get_signature(by_permission)
    identifier = KeyBuilder.build_identifier(
        "permission:{{permission}}", by_permission, signature, (None, "system:user:query"), {}
    )
    check(
        "C2 现网单占位符模板行为不变",
        identifier == "permission:system:user:query",
        f"identifier={identifier}",
    )


def test_serializer():
    serializer = CacheSerializer()
    ok_str = serializer.deserialize('{"a":1}') == {"a": 1}
    ok_bytes = serializer.deserialize(b'{"a":1}') == {"a": 1}
    try:
        serializer.deserialize(None)
    except CacheException as error:
        ok_none = error.error_code.code == CacheErrorCodes.DESERIALIZATION_FAILED.code
    else:
        ok_none = False
    check(
        "D 反序列化 str/bytes 正常，契约外输入仍报 DESERIALIZATION_FAILED",
        ok_str and ok_bytes and ok_none,
        f"str={ok_str} bytes={ok_bytes} none={ok_none}",
    )


def test_resolve_client_passthrough():
    class LockStub:
        _cache_manager = CacheManager()

    resolve = DistributedLock._resolve_client.__get__(LockStub(), LockStub)
    try:
        resolve("default")
    except CacheException as error:
        code = error.error_code.code
    else:
        code = None
    check(
        "E 缓存未就绪透传 NOT_INITIALIZED（不再误报 CLIENT_NOT_FOUND）",
        code == CacheErrorCodes.NOT_INITIALIZED.code,
        f"code={code}",
    )


PUBLICATION_SNAPSHOT = (
    CacheGenerationState(
        generation_key="cache_generation:prefix:review",
        epoch="e" * 8,
        version=1,
        state=CacheGenerationStateEnum.FINALIZED,
    ),
)


class FailingDeleter:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    async def delete_if_value_matches(self, client, full_key, expected):
        self.calls += 1
        raise self.error


def make_publisher(deleter, *, snapshot_is_current):
    publisher = CacheGenerationPublisher()

    async def is_current(client, snapshot):
        return snapshot_is_current

    publisher._coordinator = SimpleNamespace(
        snapshot_allows_publication=lambda snapshot: True,
        snapshot_is_current=is_current,
    )
    publisher._deleter = deleter
    return publisher


async def test_read_compensation_failure_keeps_error_code():
    boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="补偿删除失败")
    deleter = FailingDeleter(boom)
    publisher = make_publisher(deleter, snapshot_is_current=False)
    envelope = CacheGenerationPublisher.build_envelope(b'"v"', PUBLICATION_SNAPSHOT)
    client = SimpleNamespace(get=lambda full_key: _value(envelope))
    try:
        await publisher.read(client, "review:key")
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "F1 清理作废信封失败：原样抛缓存异常，不包成异常组",
        raised is boom and deleter.calls == 1,
        f"raised={raised!r} calls={deleter.calls}",
    )


async def test_publish_compensation_failure_keeps_error_code():
    boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="撤销写入失败")
    deleter = FailingDeleter(boom)
    publisher = make_publisher(deleter, snapshot_is_current=False)

    async def eval_applied(*args):
        return 1

    try:
        await publisher.publish(
            SimpleNamespace(eval=eval_applied), "review:key", b'"v"', 60, PUBLICATION_SNAPSHOT
        )
    except BaseException as error:
        raised = error
    else:
        raised = None
    check(
        "F2 快照过期后撤销失败：原样抛缓存异常，不包成异常组",
        raised is boom and deleter.calls == 1,
        f"raised={raised!r} calls={deleter.calls}",
    )


async def test_publish_primary_error_still_wins():
    cleanup_boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="撤销写入失败")
    write_boom = CacheException(CacheErrorCodes.OPERATION_FAILED, msg="CAS 写入失败")
    deleter = FailingDeleter(cleanup_boom)
    publisher = make_publisher(deleter, snapshot_is_current=True)

    async def eval_failing(*args):
        raise write_boom

    try:
        await publisher.publish(
            SimpleNamespace(eval=eval_failing), "review:key", b'"v"', 60, PUBLICATION_SNAPSHOT
        )
    except BaseException as error:
        raised = error
    else:
        raised = None
    cause = getattr(raised, "__cause__", None)
    check(
        "F3 主异常仍优先，补偿失败经异常链保留（行为不变）",
        raised is write_boom
        and isinstance(cause, BaseExceptionGroup)
        and cleanup_boom in cause.exceptions,
        f"raised={raised!r} cause={type(cause).__name__}",
    )


async def test_publish_compensation_success_is_silent():
    class SilentDeleter:
        def __init__(self):
            self.calls = 0

        async def delete_if_value_matches(self, client, full_key, expected):
            self.calls += 1
            return 1

    deleter = SilentDeleter()
    publisher = make_publisher(deleter, snapshot_is_current=False)

    async def eval_applied(*args):
        return 1

    published = await publisher.publish(
        SimpleNamespace(eval=eval_applied), "review:key", b'"v"', 60, PUBLICATION_SNAPSHOT
    )
    check(
        "F4 补偿成功时返回未发布而不是抛错（行为不变）",
        published is False and deleter.calls == 1,
        f"published={published} calls={deleter.calls}",
    )
