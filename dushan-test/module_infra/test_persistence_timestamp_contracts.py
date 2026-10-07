from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fixtures.config_factory import ConfigFactory
from framework.common.dates import DateTimeOptions, DateUtils
from framework.starter_mq.public import MessageEnvelope, MessageMode, PreparedMessage
from module_infra.spi.job.tenant_job_target_provider_adapter import TenantJobTargetProviderAdapter
from module_infra.spi.mq.outbox_provider_adapter import OutboxProviderAdapter


@pytest.mark.parametrize("claimed", [True, False])
async def test_tenant_target_passes_exact_lease_and_now_microseconds_to_mapper(claimed):
    """认领与结算使用同一整数微秒规则，拒领仍保持原有空返回。"""
    adapter = TenantJobTargetProviderAdapter()
    adapter.date_utils = DateUtils(ConfigFactory.build(DateTimeOptions, "datetime", timezone="UTC"))
    adapter.mapper = SimpleNamespace(claim=AsyncMock(return_value=claimed), settle=AsyncMock())
    lease = await adapter.claim("request", "2", 1.000001)
    row, now_us = adapter.mapper.claim.await_args.args
    assert row.expires_at_us - now_us == 1_000_001
    assert (row.request_id, row.tenant_id, row.state) == ("request", "2", "claimed")
    if not claimed:
        assert lease is None
        return
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    assert lease.expires_at == epoch + timedelta(microseconds=row.expires_at_us)
    await adapter.complete(lease)
    completed = adapter.mapper.settle.await_args.args
    assert completed[:5] == ("request", "2", lease.token, row.expires_at_us, "completed")
    await adapter.release(lease)
    released = adapter.mapper.settle.await_args.args
    assert released[:5] == ("request", "2", lease.token, row.expires_at_us, "pending")


@pytest.mark.parametrize("optional_timestamp", [None, -1, 253_402_271_999_999_999])
def test_outbox_record_restores_exact_timestamp_and_optional_fields(optional_timestamp):
    """Outbox 恢复消息时精确保留微秒、空字段与相同绝对时间。"""
    adapter = OutboxProviderAdapter()
    adapter.date_utils = DateUtils(
        ConfigFactory.build(DateTimeOptions, "datetime", timezone="Asia/Shanghai")
    )
    message = PreparedMessage(
        mode=MessageMode.STREAM,
        envelope=MessageEnvelope(
            version=1,
            message_id="1" * 32,
            destination="events",
            authority="session",
            capability=None,
            tenant_id="2",
            proof="dGVzdA==",
            payload="dGVzdA==",
            issued_at=1.0,
            expires_at=3601.0,
            attempt=0,
            ready_at=1.0,
            consumer_key=None,
            trace_headers={},
            signature="0" * 64,
        ),
    )
    row = SimpleNamespace(
        record_id="record",
        message=message.model_dump_json(),
        state="pending",
        attempts=0,
        created_at_us=-1,
        ready_at_us=1_765_432_109_654_321,
        claim_token=None,
        claim_expires_at_us=optional_timestamp,
        finished_at_us=optional_timestamp,
        error_type=None,
    )
    record = adapter.record(row)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    assert record.message == message
    assert record.created_at == epoch - timedelta(microseconds=1)
    assert record.ready_at == epoch + timedelta(microseconds=row.ready_at_us)
    assert record.created_at.tzinfo is UTC
    assert record.ready_at.tzinfo is UTC
    expected = (
        None if optional_timestamp is None else epoch + timedelta(microseconds=optional_timestamp)
    )
    assert record.claim_expires_at == expected
    assert record.finished_at == expected
