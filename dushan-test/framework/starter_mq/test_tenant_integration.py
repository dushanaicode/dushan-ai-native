from uuid import uuid4

import pytest
from sqlalchemy import update
from starter_tenant.conftest import TenantCase

from framework.starter_mq.model.publish_command import PublishCommand
from framework.starter_web.routing.route_policy import RoutePolicy


@pytest.mark.parametrize("mq_sql_options", [{"tenant": True}], indirect=True)
async def test_tenant_propagation_isolated_in_real_sql_queries(mq_sql_case):
    case = mq_sql_case
    message_id = uuid4().hex
    await case.publish(1, tenant_id="1", message_id=message_id)
    await case.publish(2, tenant_id="2", message_id=message_id)
    await case.until(lambda: len(case.probe.records) == 2)
    assert sorted(case.probe.visible) == [("1", ["1", "1"]), ("2", ["2"])]
    assert [record.state.value for record in case.probe.records] == ["succeeded", "succeeded"]
    assert all(not execution.active for execution in case.probe.executions)


@pytest.mark.parametrize("mq_sql_options", [{"tenant": True}], indirect=True)
async def test_tenant_disabled_after_publish_preparation_is_rejected(mq_sql_case):
    case = mq_sql_case
    prepared = await case.prepare(1, tenant_id="1")
    async with case.engine.begin() as connection:
        await connection.execute(
            update(case.tenant_module.Directory)
            .where(case.tenant_module.Directory.tenant_key == "1")
            .values(enabled=False)
        )
    await case.service.send_prepared(prepared)
    await case.until(lambda: len(case.probe.records) == 1)
    assert not case.probe.runs and not case.probe.visible
    assert case.probe.records[0].state.value == "rejected"


@pytest.mark.parametrize(
    "mq_sql_options", [{"tenant": True, "session": True, "permissions": True}], indirect=True
)
async def test_member_message_restores_tenant_and_data_permission(mq_sql_case):
    case = mq_sql_case
    token, identity = TenantCase.issue(case)

    async def publish():
        return await case.service.publish(
            PublishCommand("events", case.module.definition.mode, case.module.Payload(value=1))
        )

    await case.app.state.security.run(
        token, RoutePolicy(tenant_required=True, permissions=("read",)), publish
    )
    await case.until(lambda: len(case.probe.records) == 1)
    assert case.probe.visible == [("1", ["1"])]
    assert case.probe.records[0].state.value == "succeeded"
    assert len(case.probe.runs) == 1


@pytest.mark.parametrize(
    "mq_sql_options", [{"tenant": True, "session": True, "permissions": True}], indirect=True
)
async def test_member_revision_is_rechecked_on_retry(mq_sql_case):
    case = mq_sql_case
    token, identity = TenantCase.issue(case)
    await case.app.state.security.run(
        token,
        RoutePolicy(tenant_required=True, permissions=("read",)),
        lambda: case.service.publish(
            PublishCommand(
                "events",
                case.module.definition.mode,
                case.module.Payload(value=1, behavior="retry"),
            )
        ),
    )
    await case.until(lambda: len(case.probe.records) == 1)
    case.tokens.sessions[identity.token_digest] = identity.model_copy(
        update={"authorization_revision": "2"}
    )
    await case.until(lambda: len(case.probe.records) == 2)
    assert len(case.probe.runs) == 1
    assert [record.state.value for record in case.probe.records] == ["retry", "rejected"]
