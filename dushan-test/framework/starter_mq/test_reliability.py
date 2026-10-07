import asyncio
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer

from framework.starter_mq.core import consumer_runner


async def dead_letter(case):
    backend = case.runtime.backend
    definition = case.module.definition
    async with asyncio.timeout(12):
        if definition.mode.value == "stream":
            rows = await backend.client.xread(
                {backend.dlq(definition): "0-0"}, count=1, block=10000
            )
            assert rows
            return json.loads(rows[0][1][0][1]["body"])
        if definition.mode.value == "queue":
            arguments = backend._arguments(case.runtime.settings.dead_letter_max_length)
            arguments["x-message-ttl"] = case.runtime.settings.dead_letter_retention_seconds * 1000
            queue = await backend._declare(backend.dlq(definition), arguments)
            async with queue.iterator() as messages:
                message = await anext(messages)
                await message.ack()
                return json.loads(message.body)
        await backend._declare(backend.dlq(definition), dead_letter=True)
        consumer = AIOKafkaConsumer(
            backend.dlq(definition),
            **backend.connection_options(),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            group_id="test-dlq-" + uuid4().hex,
        )
        try:
            await consumer.start()
            message = await consumer.getone()
            return json.loads(message.value)
        finally:
            await consumer.stop()


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize(
    "mq_options", [{"delay": 0.8, "settings": {"concurrency": 1, "prefetch": 4}}], indirect=True
)
async def test_durable_retry_frees_business_slot(mq_case, monkeypatch):
    case = mq_case
    retry_messages = []
    retry = case.runtime.backend.retry
    prepared = await case.prepare(1, behavior="retry")
    now = time.time()

    async def hold_retry(definition, envelope, body):
        """保留重试投递，直到第二条消息证明业务并发名额已经释放。"""
        retry_messages.append((definition, envelope, body))

    monkeypatch.setattr(case.runtime.backend, "retry", hold_retry)
    monkeypatch.setattr(
        consumer_runner, "time", SimpleNamespace(time=lambda: now, monotonic=time.monotonic)
    )
    await case.service.send_prepared(prepared)
    await case.until(lambda: len(case.probe.records) >= 1)
    assert len(retry_messages) == 1
    assert retry_messages[0][1].ready_at == now + 0.8
    monkeypatch.setattr(consumer_runner, "time", time)
    await case.publish(2)
    await case.until(lambda: len(case.probe.records) == 2)
    assert case.probe.finished == [2]
    monkeypatch.setattr(case.runtime.backend, "retry", retry)
    await retry(*retry_messages[0])
    await case.until(lambda: len(case.probe.records) == 3)
    assert [(value, attempt) for value, attempt, *_ in case.probe.runs] == [(1, 0), (2, 0), (1, 1)]
    assert case.probe.peak == 1
    assert case.probe.finished == [2, 1]


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize(
    "behavior,attempts,state",
    [("fail", [0, 1, 2], "retry"), ("reject", [0], "rejected"), ("unknown", [0], "unknown")],
)
async def test_exhaustion_rejection_and_unknown_dead_letter(mq_case, behavior, attempts, state):
    case = mq_case
    await case.publish(1, behavior=behavior)
    await case.until(lambda: len(case.probe.records) == len(attempts))
    assert [item[1] for item in case.probe.runs] == attempts
    item = await dead_letter(case)
    assert item["state"] == state
    assert item["replayable"] is (behavior != "unknown")
    assert (item["envelope"] is None) is (behavior == "unknown")
    assert "sensitive-mq-payload" not in json.dumps(item)


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_duplicate_id_does_not_execute_twice(mq_case):
    case = mq_case
    prepared = await case.prepare(1, behavior="wait")
    await case.service.send_prepared(prepared)
    await case.until(lambda: len(case.probe.runs) == 1)
    await case.service.send_prepared(prepared)
    case.probe.gate.set()
    await case.until(lambda: len(case.probe.records) == 1)
    await case.publish(2)
    await case.until(lambda: 2 in case.probe.finished)
    assert [row[0] for row in case.probe.runs].count(1) == 1


@pytest.mark.parametrize("mq_backend", ["stream", "rabbitmq", "kafka"], indirect=True)
@pytest.mark.parametrize("mq_options", [{"exhausted": "discard", "retries": 0}], indirect=True)
async def test_explicit_discard_records_failure_and_continues(mq_case):
    case = mq_case
    await case.publish(1, behavior="fail")
    await case.until(lambda: len(case.probe.records) == 1)
    await case.publish(2)
    await case.until(lambda: 2 in case.probe.finished)
    assert len(case.probe.runs) == 2
    assert case.probe.records[0].error_type == "ValueError"
    assert not case.runtime.paused


@pytest.mark.parametrize("mq_backend", ["stream", "pubsub", "rabbitmq", "kafka"], indirect=True)
async def test_observation_failure_does_not_repeat_success(mq_case):
    case = mq_case
    case.probe.record_failure = True
    case.probe.cleanup_failure = True
    await case.publish(1)
    await case.until(lambda: 1 in case.probe.finished)
    await asyncio.gather(*tuple(case.runtime.pending))
    assert case.runtime.resources()["observation_failures"] == 2
    assert len(case.probe.runs) == 1
    assert case.probe.contexts[0][0] == "enter"
    assert case.probe.contexts[1][0] == "exit"
