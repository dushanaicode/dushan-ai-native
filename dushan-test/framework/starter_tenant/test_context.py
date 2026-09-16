import asyncio

import pytest
from sqlalchemy import select, update

from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_tenant.exception.tenant_exception import TenantException


async def test_parallel_nested_cancel_and_inherited_context(tenant_case):
    case = tenant_case
    first, _ = case.issue(tenant="1")
    second, _ = case.issue(tenant="2")

    async def read(token):
        async with case.enter(token):
            await asyncio.sleep(0)
            async with case.database.read_session() as session:
                return sorted((await session.scalars(select(case.module.Record.id))).all())

    assert await asyncio.gather(read(first), read(second)) == [[1, 2], [3]]
    async with case.enter(first):
        frame = case.tenant.context.current()
        assert await asyncio.to_thread(case.tenant.context.get_required_tenant_id) == "1"
        async with case.enter(second):
            assert case.tenant.context.get_required_tenant_id() == "2"
        assert case.tenant.context.current() is frame
    release = asyncio.Event()

    async def inherited():
        await release.wait()
        with pytest.raises(TenantException):
            case.tenant.context.current()

    async with case.enter(first):
        child = asyncio.create_task(inherited())
    release.set()
    await child
    started = asyncio.Event()

    async def wait():
        async with case.enter(first):
            started.set()
            await asyncio.Future()

    task = asyncio.create_task(wait())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert case.tenant.context._active == 0


async def test_unavailable_foreign_membership_and_provider_failure(tenant_case):
    case = tenant_case
    bad, _ = case.issue(member="unknown")
    with pytest.raises(TenantException):
        async with case.enter(bad):
            pass
    unknown, _ = case.issue(tenant="unknown")
    with pytest.raises(TenantException, match="不存在"):
        async with case.enter(unknown):
            pass
    async with case.engine.begin() as connection:
        await connection.execute(
            update(case.module.Directory)
            .where(case.module.Directory.tenant_key == "1")
            .values(enabled=False)
        )
    with pytest.raises(TenantException, match="不可用"):
        async with case.enter():
            pass
    case.tenant.directory.failure = RuntimeError("private-provider-detail")
    with pytest.raises(SecurityException) as failure:
        async with case.enter():
            pass
    assert str(failure.value) == "安全依赖暂不可用"
    assert isinstance(failure.value.__cause__, TenantException)
    assert isinstance(failure.value.__cause__.__cause__, RuntimeError)
    assert case.tenant.context._active == 0
