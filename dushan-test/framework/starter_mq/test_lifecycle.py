import asyncio

import pytest

from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.exception.mq_exception import MQException
from starter_mq.test_reliability import dead_letter


async def eligible_pending(case):
    if case.module.definition.mode.value == "stream":
        backend = case.runtime.backend
        for key in (backend.stream("events"), backend.retry_stream(case.module.definition)):
            rows = await backend.client.xpending_range(key, "test-group", "-", "+", 50)
            if rows:
                await backend.client.xclaim(
                    key,
                    "test-group",
                    "boundary-probe",
                    0,
                    [row["message_id"] for row in rows],
                    idle=int(case.runtime.settings.lease_seconds * 1000) + 1,
                    justid=True,
                )


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_bounded_inflight_and_cancelled_delivery_recovery(mq_case):
    case = mq_case
    await asyncio.gather(*(case.publish(value, behavior="wait") for value in range(6)))
    expected = 1 if case.module.definition.mode.value == "topic" else 2
    await case.until(lambda: case.probe.active == expected)
    assert case.probe.peak == expected
    assert case.runtime.resources()["inflight"] <= 4
    await case.runtime.close()
    assert case.probe.active == 0
    assert case.runtime.resources()["inflight"] == 0
    assert not case.probe.finished
    await eligible_pending(case)
    peer = await case.peer()
    peer.probe.gate.set()
    if case.module.definition.mode.value == "pubsub":
        await peer.publish(10)
        await peer.until(lambda: peer.probe.finished == [10])
    else:
        await peer.until(lambda: len(peer.probe.finished) == 6)
        assert sorted(peer.probe.finished) == list(range(6))


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
async def test_dead_letter_failure_does_not_ack_or_repeat_business(mq_case, monkeypatch):
    case = mq_case

    async def unavailable(*args):
        raise OSError("controlled DLQ persistence failure")

    monkeypatch.setattr(case.runtime.backend, "dead_letter", unavailable)
    await case.publish(1, behavior="reject")
    await case.until(lambda: len(case.probe.records) == 1)
    await asyncio.gather(*tuple(case.runtime.pending))
    assert "controlled" in case.runtime.paused
    await case.runtime.close()
    await eligible_pending(case)
    peer = await case.peer()
    item = await dead_letter(peer)
    assert item["state"] == "rejected"
    await asyncio.gather(*tuple(peer.runtime.pending))
    assert not peer.probe.runs
    assert len(case.probe.runs) == 1


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize("mq_options", [{"exhausted": "hold", "retries": 0}], indirect=True)
async def test_explicit_hold_keeps_message_unacknowledged(mq_case):
    case = mq_case
    await case.publish(1, behavior="reject")
    await case.until(lambda: len(case.probe.records) == 1)
    await asyncio.gather(*tuple(case.runtime.pending))
    assert "controlled" in case.runtime.paused
    if case.module.definition.mode.value == "stream":
        assert (
            await case.runtime.backend.client.xpending(
                case.runtime.backend.stream("events"), "test-group"
            )
        )["pending"] == 1
    await case.runtime.close()
    await eligible_pending(case)
    peer = await case.peer()
    # 再启应用仍读到持久 HOLD，不重新执行业务或自动丢弃。
    await asyncio.wait_for(peer.runtime.actors["controlled"], timeout=5)
    assert "controlled" in peer.runtime.paused
    assert not peer.probe.runs


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
async def test_publish_confirmation_timeout_is_unknown(mq_case, monkeypatch):
    case = mq_case
    prepared = await case.prepare(1)
    original = case.runtime.backend.publish

    async def lose_confirmation(*args):
        result = await original(*args)
        await asyncio.Event().wait()
        return result

    monkeypatch.setattr(case.runtime.backend, "publish", lose_confirmation)
    case.runtime.settings = case.runtime.settings.model_copy(
        update={"command_timeout_seconds": 0.15}
    )
    with pytest.raises(MQException) as failure:
        await case.service.send_prepared(prepared)
    assert failure.value.error_code is MQErrorCodes.UNKNOWN
    await case.until(lambda: 1 in case.probe.finished)
    assert len(case.probe.runs) == 1


async def test_close_waiter_cancellation_preserves_owned_cleanup(mq_case):
    case = mq_case
    await case.publish(1, behavior="wait")
    await case.until(lambda: case.probe.active == 1)
    closer = asyncio.create_task(case.runtime.close())
    await asyncio.sleep(0)
    closer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await closer
    case.probe.gate.set()
    await case.runtime.close()
    assert case.runtime.resources()["state"] == "closed"
    assert case.runtime.resources()["inflight"] == 0


@pytest.mark.parametrize(
    "mq_options", [{"settings": {"handler_timeout_seconds": 0.1}}], indirect=True
)
async def test_cancellation_resistant_handler_keeps_slot_until_exit(mq_case):
    case = mq_case
    await case.publish(1, behavior="resist")
    await asyncio.wait_for(case.probe.cancelled.wait(), timeout=3)
    assert case.probe.active == 1
    assert case.runtime.cancelling == 1
    assert not case.probe.records
    case.probe.gate.set()
    await case.until(lambda: len(case.probe.records) == 1)
    assert case.probe.records[0].state.value == "succeeded"
    assert case.runtime.cancelling == 0


async def test_cache_connection_interrupt_is_diagnosed(mq_case):
    case = mq_case
    # 在服务端确认当前阻塞 XREADGROUP 后，只断开这一条本轮读连接。
    async with asyncio.timeout(3):
        while True:
            clients = await case.runtime.replay.client.client_list()
            readers = [client for client in clients if client["cmd"] == "xreadgroup"]
            if readers:
                assert len(readers) == 1
                await case.runtime.replay.client.client_kill_filter(_id=readers[0]["id"])
                break
            await asyncio.sleep(0)
    await asyncio.wait_for(case.runtime.actors["controlled"], timeout=3)
    assert "controlled" in case.runtime.paused
    assert case.runtime.resources()["background_error_types"]
