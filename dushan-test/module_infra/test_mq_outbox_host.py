from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import create_async_engine

from framework.starter_database.public import SessionProvider
from framework.starter_job.public import TenantJobTargetProvider
from framework.starter_mq.jobs.outbox_job import OutboxJob
from framework.starter_mq.model.outbox_job_parameters import OutboxJobParameters
from framework.starter_mq.public import (
    MessageEnvelope,
    MessageMode,
    OutboxProvider,
    PreparedMessage,
)
from framework.starter_security.public import SecurityErrorCodes, SecurityException
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO
from module_infra.spi.job.tenant_job_target_provider_adapter import TenantJobTargetProviderAdapter
from module_infra.spi.mq.outbox_provider_adapter import OutboxProviderAdapter
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from server.starter_server import StarterServer

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def test_real_host_outbox_job_uses_registered_providers_and_tenant_scope(
    infra_app, infra_database, tmp_path_factory
):
    """真实宿主开启 Outbox，逐租户补扫只清理自己的终态记录且拒绝全局身份。"""
    values = yaml.safe_load(
        (infra_app.state.bootstrap.base_dir / "application.yaml").read_text(encoding="utf-8")
    )
    suffix = uuid4().hex
    for name in ("job", "mq", "websocket"):
        values["config"]["models"][name]["namespace"] = "outbox-host-" + suffix
    values["config"]["models"]["database"]["snowflake_machine_id"] = 924
    folder = tmp_path_factory.mktemp("outbox-host-config")
    (folder / "application.yaml").write_text(
        yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
    )
    app = StarterServer.create_app(
        base_dir=folder, app_env="dev", environ={"MQ_OUTBOX_ENABLED": "true"}
    )
    resources, database_name, _ = infra_database
    engine = create_async_engine(
        f"mysql+aiomysql://root@127.0.0.1:{resources['mysql_port']}/{database_name}?charset=utf8mb4"
    )
    second_tenant_id = int(uuid4().hex[:12], 16)
    tenants = ("1", str(second_tenant_id))
    record_id = "host-" + suffix
    now = datetime.now(UTC)
    retired = now - timedelta(days=8)
    audit = dict(create_time=now.replace(tzinfo=None), update_time=now.replace(tzinfo=None))
    try:
        async with engine.begin() as connection:
            await connection.execute(
                insert(TenantDO).values(
                    id=second_tenant_id,
                    name="Outbox host test",
                    contact_name="test",
                    status=1,
                    package_id=0,
                    account_count=1,
                    **audit,
                )
            )
            for tenant_id in tenants:
                message = PreparedMessage(
                    mode=MessageMode.STREAM,
                    envelope=MessageEnvelope(
                        version=1,
                        message_id=uuid4().hex,
                        destination="events",
                        authority="session",
                        capability=None,
                        tenant_id=tenant_id,
                        proof="dGVzdA==",
                        payload="dGVzdA==",
                        issued_at=retired.timestamp(),
                        expires_at=retired.timestamp() + 3600,
                        attempt=0,
                        ready_at=retired.timestamp(),
                        consumer_key=None,
                        trace_headers={},
                        signature="0" * 64,
                    ),
                )
                await connection.execute(
                    insert(MqOutboxDO).values(
                        tenant_id=tenant_id,
                        record_id=record_id,
                        message=message.model_dump_json(),
                        state="cancelled",
                        attempts=0,
                        created_at_us=app.state.bootstrap.date_utils.to_timestamp_micros(retired),
                        ready_at_us=app.state.bootstrap.date_utils.to_timestamp_micros(retired),
                        finished_at_us=app.state.bootstrap.date_utils.to_timestamp_micros(retired),
                        **audit,
                    )
                )
        async with app.router.lifespan_context(app):
            with app.state.application_context.execution():
                container = app.state.application_context.container
                provider = container.get(OutboxProvider)
                targets = container.get(TenantJobTargetProvider)
                assert isinstance(provider, OutboxProviderAdapter)
                assert isinstance(targets, TenantJobTargetProviderAdapter)
                assert app.state.mq.outbox is provider
                assert app.state.job.tenant_runner.targets is targets
                job = container.get(OutboxJob)
                database = container.get(SessionProvider)

            async def dispatch():
                tenant_id = app.state.tenant.context.get_required_tenant_id()
                async with database.read_session(force_primary=True) as session:
                    rows = (
                        await session.scalars(
                            select(MqOutboxDO.tenant_id).where(MqOutboxDO.record_id == record_id)
                        )
                    ).all()
                assert rows == [tenant_id]
                return await job.execute(OutboxJobParameters(), None)

            for tenant_id in tenants:
                result = await app.state.security.run_workload(
                    "mq.outbox", dispatch, capability="mq.outbox.dispatch", tenant_id=tenant_id
                )
                assert result["cleaned"] == 1
                assert sum(value for key, value in result.items() if key != "cleaned") == 0
            with pytest.raises(SecurityException) as error:
                await app.state.security.run_workload(
                    "mq.outbox", dispatch, capability="mq.outbox.dispatch", tenant_id=None
                )
            assert error.value.error_code is SecurityErrorCodes.DENIED
            assert "按租户逐个执行" in str(error.value)
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(MqOutboxDO).where(MqOutboxDO.record_id == record_id))
            await connection.execute(delete(TenantDO).where(TenantDO.id == second_tenant_id))
        await engine.dispose()
