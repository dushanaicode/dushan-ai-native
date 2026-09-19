import pytest
from sqlalchemy import select, update

from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_web.routing.route_policy import RoutePolicy


@pytest.mark.parametrize("tenant_case", [{"profile": "internal_group"}], indirect=True)
async def test_group_managed_target_revalidates_authority_and_relation(tenant_case):
    case = tenant_case
    token, _ = case.issue(
        tenant="2",
        membership_id=None,
        dept_id=None,
        authority_tenant_id="1",
        authority_membership_id="m1",
        group_id="g1",
        management_relation_id="r1",
        access_mode=TenantAccessMode.GROUP_MANAGED,
        effective_capabilities=frozenset({"group_managed_access"}),
    )
    policy = RoutePolicy(
        realm=SecurityRealm.TENANT,
        permissions=("read",),
        allowed_tenant_access_modes=frozenset({TenantAccessMode.GROUP_MANAGED}),
        required_capability="group_managed_access",
        required_entitlement="group_managed_access",
    )
    with case.app.state.application_context.execution():
        async with case.app.state.security.authorized(token, policy):
            async with case.database.read_session() as session:
                assert (await session.scalars(select(case.module.Record.id))).all() == [3]
        async with case.engine.begin() as connection:
            await connection.execute(
                update(case.module.AccessApproval)
                .where(case.module.AccessApproval.kind == "managed")
                .values(enabled=False)
            )
        with pytest.raises(TenantException):
            async with case.app.state.security.authorized(token, policy):
                pass


async def test_support_session_requires_live_scoped_approval(tenant_case):
    case = tenant_case
    resource = case.module.Record.__table__.key
    token, _ = case.issue(
        realm=SecurityRealm.SUPPORT,
        membership_id=None,
        dept_id=None,
        authority_tenant_id=None,
        authority_membership_id=None,
        access_mode=None,
        platform_operator_id="op1",
        support_session_id="support-approved",
        approved_resource=resource,
        approved_action="read",
        effective_capabilities=frozenset({"support_session"}),
    )
    policy = RoutePolicy(
        realm=SecurityRealm.SUPPORT,
        required_capability="support_session",
        required_entitlement="support_session",
        required_support_resource=resource,
        required_support_action="read",
    )
    with case.app.state.application_context.execution():
        async with case.app.state.security.authorized(token, policy):
            assert case.tenant.context.get_required_tenant_id() == "1"
            async with case.database.read_session() as session:
                assert (
                    await session.scalars(
                        select(case.module.Record.id).order_by(case.module.Record.id)
                    )
                ).all() == [1, 2]
            with pytest.raises(TenantException):
                async with case.database.transaction() as session:
                    await session.execute(
                        update(case.module.Record)
                        .where(case.module.Record.id == 1)
                        .values(value=55)
                    )
        async with case.engine.begin() as connection:
            await connection.execute(
                update(case.module.AccessApproval)
                .where(case.module.AccessApproval.kind == "support")
                .values(enabled=False)
            )
        with pytest.raises(TenantException):
            async with case.app.state.security.authorized(token, policy):
                pass
