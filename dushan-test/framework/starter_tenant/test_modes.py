import pytest
from sqlalchemy import delete, select

from framework.starter_tenant.core.deployment_mode_store import DeploymentModeStore
from framework.starter_tenant.exception.tenant_exception import TenantException


@pytest.mark.parametrize("tenant_case", [{"empty": True}], indirect=True)
async def test_enabled_empty_directory_is_ready_without_fabricated_tenant(tenant_case):
    case = tenant_case
    with case.app.state.application_context.execution():
        assert await case.tenant.targets() == ()
    with pytest.raises(TenantException, match="不存在"):
        async with case.enter():
            pass


@pytest.mark.parametrize("tenant_case", [{"enabled": False}], indirect=True)
async def test_disabled_mode_keeps_filtering_and_only_default_target(tenant_case):
    case = tenant_case
    with case.app.state.application_context.execution():
        assert await case.tenant.targets() == ("1",)
    async with case.enter():
        async with case.database.read_session() as session:
            assert (
                await session.scalars(select(case.module.Record.id).order_by(case.module.Record.id))
            ).all() == [1, 2]
    other, _ = case.issue(tenant="2")
    with pytest.raises(TenantException):
        async with case.enter(other):
            pass


async def test_sealed_mode_transition_and_mismatch(tenant_case):
    case = tenant_case
    desired = case.tenant.settings.model_copy(update={"enabled": False})
    with case.app.state.application_context.execution():
        with pytest.raises(TenantException, match="模式"):
            await case.tenant.mode.transition(desired, case.tenant.directory)
    async with case.engine.begin() as connection:
        await connection.execute(
            delete(case.module.Directory).where(case.module.Directory.tenant_key == "2")
        )
    with case.app.state.application_context.execution():
        await case.tenant.mode.transition(desired, case.tenant.directory)
        with pytest.raises(TenantException, match="模式"):
            await case.tenant.mode.claim()
        new = DeploymentModeStore(case.database, desired)
        await new.claim()
        await new.transition(case.tenant.settings, case.tenant.directory)
        await case.tenant.mode.claim()
