import asyncio
import base64
import json
import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pymysql
import pytest
from pydantic import SecretStr
from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.config_factory import ConfigFactory
from framework.common.dates import DateTimeOptions, DateUtils
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_database.public import DatabaseSettings, SessionProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.di_container import DiContainer
from framework.starter_mq.core.consumer_runner import ConsumerRunner
from framework.starter_mq.core.message_codec import MessageCodec
from framework.starter_mq.public import (
    MessageEnvelope,
    MessageMode,
    MQErrorCodes,
    MQException,
    MQService,
    OutboxRecord,
    OutboxService,
    OutboxState,
    PreparedMessage,
    PublishReceipt,
)
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_session_policy import TenantSessionPolicy
from framework.starter_tenant.public import TenantContext, TenantException
from module_infra.dal.dataobject.job.job_signal_do import JobSignalDO
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO
from module_infra.dal.mapper.mq.mq_outbox_mapper import MqOutboxMapper
from module_infra.spi.mq.outbox_provider_adapter import OutboxProviderAdapter


class OutboxCase:
    def __init__(self, application, database, tenant, store, engine):
        self.application, self.database, self.tenant, self.store, self.engine = (
            application,
            database,
            tenant,
            store,
            engine,
        )
        self.settings = SimpleNamespace(
            signing_secret=SecretStr("outbox-persistence-test-secret"),
            max_message_bytes=1_000_000,
            max_proof_bytes=65536,
            clock_skew_seconds=5,
            max_age_seconds=3600,
            outbox_enabled=True,
            outbox_batch_size=10,
            outbox_lease_seconds=30,
            outbox_max_attempts=3,
            outbox_retry_seconds=1,
            max_retry_delay_seconds=10,
            command_timeout_seconds=2,
            renew_seconds=1,
        )
        self.codec = MessageCodec(self.settings)

    @contextmanager
    def enter(self, tenant_id="1"):
        with self.application.execution(), self.database.scope():
            with self.tenant._bind(tenant_id, None, seconds=60):
                yield

    def record(self, identifier=None, *, tenant_id="1", attempts=0, payload=b"payload"):
        now = datetime.now(UTC)
        issued = int(time.time()) - 1 + 0.4418597
        envelope = self.codec.sign(
            MessageEnvelope(
                version=1,
                message_id=uuid4().hex,
                destination="events",
                authority="session",
                capability=None,
                tenant_id=tenant_id,
                proof=base64.b64encode(b"proof").decode(),
                payload=base64.b64encode(payload).decode(),
                issued_at=issued,
                expires_at=issued + 3600,
                attempt=0,
                ready_at=issued,
                consumer_key=None,
                trace_headers={},
                signature="0" * 64,
            )
        )
        return OutboxRecord(
            id=identifier or uuid4().hex,
            message=PreparedMessage(mode=MessageMode.STREAM, envelope=envelope),
            state=OutboxState.PENDING,
            attempts=attempts,
            created_at=now,
            ready_at=now,
            claim_token=None,
            claim_expires_at=None,
            finished_at=None,
            error_type=None,
        )

    async def claim(self, record_id=None, *, now=None, max_attempts=3):
        return await self.store.claim(
            now=now or datetime.now(UTC),
            lease_seconds=30,
            max_attempts=max_attempts,
            record_id=record_id,
        )

    async def rows(self):
        async with self.database.read_session(force_primary=True) as session:
            return list((await session.scalars(select(MqOutboxDO).order_by(MqOutboxDO.id))).all())


@pytest.fixture(params=["sqlite", "mysql"])
async def outbox_case(request, tmp_path, config_dir):
    admin = None
    if request.param == "mysql":
        resources_path = os.environ.get("DUSHAN_SYSTEM_RESOURCES")
        if resources_path is None:
            pytest.skip("需要固定 MySQL 测试资源清单")
        resources = json.loads(Path(resources_path).read_text(encoding="utf-8"))
        assert resources["mysql_port"] == 33170
        admin = pymysql.connect(
            host="127.0.0.1", port=33170, user="root", password="", autocommit=True
        )
        name = os.environ.get("DUSHAN_TEST_DATABASE_PREFIX", "outbox_test_") + uuid4().hex
        with admin.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4")
        url = f"mysql+aiomysql://root@127.0.0.1:33170/{name}?charset=utf8mb4"
    else:
        url = f"sqlite+aiosqlite:///{(tmp_path / 'outbox.sqlite').as_posix()}"
    engine = create_async_engine(url)
    configuration = ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [])
    application = ApplicationContext(
        DiContainer(
            (),
            configuration=configuration,
            settings=ConfigFactory.build(DiSettings, "di"),
            enabled_modules=frozenset(),
        )
    )
    settings = ConfigFactory.values()["config"]["models"]["database"]
    settings.update(
        enabled=True,
        health_check_enabled=False,
        sources=[dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)],
    )
    database = SessionProvider(DatabaseSettings.model_validate(settings))
    tenant = TenantContext(application)
    mapper = MqOutboxMapper()
    mapper.session_provider = database
    store = OutboxProviderAdapter()
    store.database, store.tenant, store.mapper = database, tenant, mapper
    store.date_utils = DateUtils(ConfigFactory.build(DateTimeOptions, "datetime"))
    try:
        async with engine.begin() as connection:
            for model in (MqOutboxDO, JobSignalDO):
                await connection.run_sync(model.__table__.create)
        await application.startup()
        application.mark_ready()
        await database.open()
        with database.use_session_policy(
            TenantSessionPolicy(TenantModelRegistry([MqOutboxDO, JobSignalDO]), tenant)
        ):
            yield OutboxCase(application, database, tenant, store, engine)
    finally:
        await database.close()
        await application.shutdown()
        configuration.close()
        await engine.dispose()
        if admin is not None:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE `{name}`")
            admin.close()


async def test_insert_shares_business_transaction_and_rejects_content_conflict(outbox_case):
    case = outbox_case
    record = case.record()
    with case.enter():
        with pytest.raises(ValueError, match="rollback"):
            async with case.database.transaction() as session:
                await session.execute(insert(JobSignalDO).values(id=1, revision=1))
                await case.store.insert(record)
                raise ValueError("rollback")
        assert await case.rows() == []
        async with case.database.read_session() as session:
            assert await session.scalar(select(func.count()).select_from(JobSignalDO)) == 0
        async with case.database.transaction() as session:
            await session.execute(insert(JobSignalDO).values(id=1, revision=1))
            await case.store.insert(record)
        await case.store.insert(record)
        assert len(await case.rows()) == 1
        with pytest.raises(MQException) as error:
            await case.store.insert(case.record(record.id))
        assert error.value.error_code is MQErrorCodes.CONFLICT
        assert (await case.rows())[0].message == record.message.model_dump_json()


async def test_claim_is_exclusive_and_independently_committed(outbox_case):
    case = outbox_case
    record = case.record()
    with case.enter():
        await case.store.insert(record)

    async def claim():
        with case.enter():
            return await case.claim(record.id)

    claims = await asyncio.gather(claim(), claim())
    assert sum(value is not None for value in claims) == 1
    claimed = next(value for value in claims if value is not None)
    assert claimed.attempts == 1 and len(claimed.claim_token) == 32
    with case.enter():
        another = case.record()
        await case.store.insert(another)
        with pytest.raises(ValueError, match="outer"):
            async with case.database.transaction():
                await case.claim(another.id)
                raise ValueError("outer")
        assert all(row.state == "sending" for row in await case.rows())


async def test_concurrent_same_record_insert_is_idempotent(outbox_case):
    case = outbox_case
    record = case.record()

    async def save():
        with case.enter():
            await case.store.insert(record)

    await asyncio.gather(save(), save())
    with case.enter():
        assert len(await case.rows()) == 1
        assert (await case.rows())[0].message == record.message.model_dump_json()


async def test_retry_replaces_token_and_expired_live_state_cannot_finish(outbox_case):
    case = outbox_case
    with case.enter():
        record = case.record()
        await case.store.insert(record)
        original = await case.claim(record.id)
        await case.store.finish(
            original,
            state=OutboxState.PENDING,
            ready_at=datetime.now(UTC),
            error_type="ConfirmationError",
            receipt=None,
        )
        retried = await case.claim(record.id)
        assert retried.claim_token != original.claim_token and retried.attempts == 2
        assert retried.message == original.message
        receipt = PublishReceipt(record.message.envelope.message_id, "stream_entry", "1-0")
        with pytest.raises(MQException) as stale:
            await case.store.finish(
                original,
                state=OutboxState.PUBLISHED,
                ready_at=datetime.now(UTC),
                error_type=None,
                receipt=receipt,
            )
        assert stale.value.error_code is MQErrorCodes.LEASE
        await case.store.mapper.write(
            update(MqOutboxDO)
            .where(MqOutboxDO.record_id == record.id)
            .values(
                claim_expires_at_us=case.store.date_utils.to_timestamp_micros(
                    datetime.now(UTC) - timedelta(microseconds=1)
                )
            )
        )
        with pytest.raises(MQException) as expired:
            await case.store.finish(
                retried,
                state=OutboxState.PUBLISHED,
                ready_at=datetime.now(UTC),
                error_type=None,
                receipt=receipt,
            )
        assert expired.value.error_code is MQErrorCodes.LEASE
        assert (await case.rows())[0].state == "sending"


async def test_microsecond_boundaries_and_expired_sending_never_replay(outbox_case):
    case = outbox_case
    now = datetime.now(UTC).replace(microsecond=654321)
    record = case.record().model_copy(update={"created_at": now, "ready_at": now})
    with case.enter():
        await case.store.insert(record)
        assert await case.claim(record.id, now=now - timedelta(microseconds=1)) is None
        claimed = await case.claim(record.id, now=now)
        assert claimed.created_at == now
        assert claimed.ready_at == now
        assert claimed.claim_expires_at == now + timedelta(seconds=30)
        assert await case.claim(record.id, now=claimed.claim_expires_at) is None
        row = (await case.rows())[0]
        assert row.state == "unknown" and row.attempts == 1
        with pytest.raises(MQException) as error:
            await case.store.finish(
                claimed,
                state=OutboxState.PUBLISHED,
                ready_at=now,
                error_type=None,
                receipt=PublishReceipt(claimed.message.envelope.message_id, "stream_entry", "1-0"),
            )
        assert error.value.error_code is MQErrorCodes.LEASE
        assert await case.store.cleanup(before=now + timedelta(days=1), limit=10) == 0


async def test_finish_requires_live_token_and_same_success_receipt_is_idempotent(outbox_case):
    case = outbox_case
    with case.enter():
        record = case.record()
        await case.store.insert(record)
        claimed = await case.claim(record.id)
        receipt = PublishReceipt(record.message.envelope.message_id, "stream_entry", "1-0")
        for invalid in (claimed.model_copy(update={"claim_token": uuid4().hex}),):
            with pytest.raises(MQException) as error:
                await case.store.finish(
                    invalid,
                    state=OutboxState.PUBLISHED,
                    ready_at=datetime.now(UTC),
                    error_type=None,
                    receipt=receipt,
                )
            assert error.value.error_code is MQErrorCodes.LEASE
        for _ in range(2):
            await case.store.finish(
                claimed,
                state=OutboxState.PUBLISHED,
                ready_at=datetime.now(UTC),
                error_type=None,
                receipt=receipt,
            )
        with pytest.raises(MQException):
            await case.store.finish(
                claimed,
                state=OutboxState.PUBLISHED,
                ready_at=datetime.now(UTC),
                error_type=None,
                receipt=PublishReceipt(receipt.message_id, "stream_entry", "2-0"),
            )
        assert not await case.store.cancel(record.id)
        assert (await case.rows())[0].state == "published"


async def test_dead_cancel_cleanup_and_tenant_isolation(outbox_case):
    case = outbox_case
    with case.enter("2"):
        other = case.record("shared", tenant_id="2")
        await case.store.insert(other)
    with case.enter():
        dead, cancelled, unknown = case.record(attempts=3), case.record("shared"), case.record()
        for record in (dead, cancelled, unknown):
            await case.store.insert(record)
        assert await case.claim(dead.id) is None
        assert await case.store.cancel(cancelled.id)
        assert not await case.store.cancel(cancelled.id)
        claimed = await case.claim(unknown.id)
        await case.store.finish(
            claimed,
            state=OutboxState.UNKNOWN,
            ready_at=datetime.now(UTC),
            error_type="ConnectionError",
            receipt=None,
        )
        assert {row.state for row in await case.rows()} == {"dead", "cancelled", "unknown"}
        before = datetime.now(UTC) + timedelta(days=1)
        assert await case.store.cleanup(before=before, limit=1) == 1
        assert await case.store.cleanup(before=before, limit=10) == 1
        assert (await case.rows())[0].state == "unknown"
        with pytest.raises(MQException) as error:
            await case.store.insert(other)
        assert error.value.error_code is MQErrorCodes.AUTHENTICATION
    with case.enter("2"):
        assert len(await case.rows()) == 1
        assert (await case.rows())[0].state == "pending"
    with case.application.execution(), case.database.scope():
        with pytest.raises(TenantException):
            await case.claim()


async def test_persistent_retry_keeps_large_signed_message_and_consumer_digest(outbox_case):
    from framework.starter_mq.definitions.enums.mq_backend import MQBackend

    case = outbox_case
    case.settings.backend = MQBackend.REDIS
    runtime = SimpleNamespace(
        settings=case.settings,
        codec=case.codec,
        phase="ready",
        outbox=case.store,
        database=case.database,
        wait_ready=AsyncMock(),
        publish_slots=asyncio.Semaphore(1),
    )
    bodies = []

    async def publish(destination, mode, body):
        bodies.append(body)
        if len(bodies) == 1:
            raise MQException(MQErrorCodes.CONFIRMATION)
        return "stream_entry", "1-0"

    async def call(awaitable):
        return await awaitable

    runtime.call = call
    runtime.backend = SimpleNamespace(publish=publish)
    mq = MQService()
    mq.runtime = runtime
    mq.prepare = AsyncMock(side_effect=AssertionError("不能重新 prepare"))
    outbox = OutboxService(mq)
    record = case.record(payload=b"x" * 100_000)
    with case.enter():
        await case.store.insert(record)
        with pytest.raises(MQException):
            await outbox.dispatch(record_id=record.id)
        row = (await case.rows())[0]
        assert row.state == "pending" and len(row.message) > 65536
        assert row.message == record.message.model_dump_json()
        await case.store.mapper.write(
            update(MqOutboxDO)
            .where(MqOutboxDO.record_id == record.id)
            .values(
                ready_at_us=case.store.date_utils.to_timestamp_micros(
                    datetime.now(UTC) - timedelta(seconds=1)
                )
            )
        )
        assert (await outbox.dispatch(record_id=record.id))["published"] == 1
        assert bodies[0] == bodies[1] == case.codec.encode(record.message.envelope)
        restored = case.codec.decode(bodies[1], "events")
        assert case.codec.digest(restored) == case.codec.digest(record.message.envelope)
        mq.prepare.assert_not_called()

    lock = SimpleNamespace(
        acquire=AsyncMock(return_value=True), release=AsyncMock(), release_required=True
    )
    runtime.replay = SimpleNamespace(
        key=lambda *args, **kwargs: "replay-key",
        lock=lambda key: lock,
        read=AsyncMock(
            return_value={
                "digest": case.codec.digest(record.message.envelope),
                "stage": "done",
                "attempt": 0,
            }
        ),
    )
    runtime.duplicates = 0
    definition = SimpleNamespace(
        external_authenticator=None, destination="events", key="worker", mode=MessageMode.STREAM
    )
    handler = SimpleNamespace(__mq_consumer__=definition)
    delivery = SimpleNamespace(
        body=bodies[1], retry=False, acknowledge=AsyncMock(), release=AsyncMock()
    )
    runner = ConsumerRunner(runtime)
    assert await runner.run(handler, delivery) == "settled"
    assert runtime.duplicates == 1
    delivery.acknowledge.assert_awaited_once()
    delivery.release.assert_not_awaited()
