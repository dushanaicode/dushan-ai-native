import pytest
from sqlalchemy import delete, select, update

from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_tenant.exception.tenant_exception import TenantException


async def test_workload_reauth_targets_and_no_inherited_tenant(tenant_case):
    case = tenant_case

    async def read():
        assert case.tenant.context.get_required_tenant_id() == "1"
        async with case.database.read_session() as session:
            return sorted((await session.scalars(select(case.module.Record.id))).all())

    token, _ = case.issue(tenant="2")
    async with case.enter(token):
        assert await case.app.state.security.run_workload(
            "maintenance", read, capability="records:maintain", tenant_id="1"
        ) == [1, 2]
        assert case.tenant.context.get_required_tenant_id() == "2"
    with case.app.state.application_context.execution():
        assert [batch async for batch in case.tenant.target_batches()] == [("1", "2")]
    with pytest.raises(SecurityException):
        await case.app.state.security.run_workload(
            "unregistered", read, capability="records:maintain", tenant_id="1"
        )
    async with case.engine.begin() as connection:
        await connection.execute(
            update(case.module.Directory)
            .where(case.module.Directory.tenant_key == "1")
            .values(enabled=False)
        )
    with pytest.raises(TenantException):
        await case.app.state.security.run_workload(
            "maintenance", read, capability="records:maintain", tenant_id="1"
        )
    assert case.tenant.context._active == 0


async def test_workload_resource_actions_and_global_scope(tenant_case):
    case = tenant_case
    case.tenant.directory.actions = frozenset({"delete"})

    async def read():
        async with case.database.read_session() as session:
            return (await session.scalars(select(case.module.Record.id))).all()

    with pytest.raises(TenantException):
        await case.app.state.security.run_workload(
            "maintenance", read, capability="records:maintain", tenant_id="1"
        )

    async def remove():
        async with case.database.transaction() as session:
            return (
                await session.execute(delete(case.module.Record).where(case.module.Record.id == 2))
            ).rowcount

    assert (
        await case.app.state.security.run_workload(
            "maintenance", remove, capability="records:maintain", tenant_id="1"
        )
        == 1
    )

    async def global_scope():
        with pytest.raises(TenantException):
            case.tenant.context.current()

    async with case.enter():
        await case.app.state.security.run_workload(
            "maintenance", global_scope, capability="records:maintain"
        )
        assert case.tenant.context.get_required_tenant_id() == "1"
