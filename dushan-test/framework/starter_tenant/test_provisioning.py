import pytest
from sqlalchemy import func, select

from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_provisioning_request import TenantProvisioningRequest
from framework.starter_web.routing.route_policy import RoutePolicy


@pytest.mark.parametrize(
    "tenant_case",
    [{"empty": True, "enabled": True}, {"empty": True, "enabled": False}],
    indirect=True,
)
async def test_first_account_provisioning_is_atomic_and_idempotent(tenant_case):
    case = tenant_case
    token, identity = case.issue(
        realm=SecurityRealm.ACCOUNT,
        tenant_id=None,
        membership_id=None,
        authority_tenant_id=None,
        authority_membership_id=None,
        dept_id=None,
        access_mode=None,
    )
    request = TenantProvisioningRequest(idempotency_key="first", name="First tenant")
    with case.app.state.application_context.execution():
        async with case.app.state.security.authorized(
            token, RoutePolicy(realm=SecurityRealm.ACCOUNT)
        ):
            case.tenant.provisioning.fail_after_directory = True
            with pytest.raises(TenantException):
                await case.tenant.provision_authenticated(request)
            case.tenant.provisioning.fail_after_directory = False
            async with case.database.read_session() as session:
                assert (
                    await session.scalar(select(func.count()).select_from(case.module.Directory))
                    == 0
                )
            created = await case.tenant.provision_authenticated(request)
            repeated = await case.tenant.provision_authenticated(request)
            assert created.tenant_id == repeated.tenant_id
            assert created.membership_id == repeated.membership_id
            assert created.created and not repeated.created
            if not case.tenant.settings.enabled:
                assert created.tenant_id == "1"
            with pytest.raises(TenantException):
                await case.tenant.provision_authenticated(
                    TenantProvisioningRequest(idempotency_key="first", name="Changed body")
                )
            async with case.database.read_session() as session:
                assert (
                    await session.scalar(select(func.count()).select_from(case.module.Directory))
                    == 1
                )
                assert (
                    await session.scalar(select(func.count()).select_from(case.module.Member)) == 1
                )
            assert case.app.state.security.context.current() is identity
    with pytest.raises(TenantException):
        case.tenant.context.current()
