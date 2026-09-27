import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiokafka import AIOKafkaProducer

from framework.starter_mq.backend.kafka_backend import KafkaBackend
from framework.starter_mq.backend.rabbit_backend import RabbitBackend
from framework.starter_mq.core.message_codec import MessageCodec
from starter_mq.test_declarations import settings


async def test_kafka_checks_real_sdk_sender_lifecycle_and_broker_metadata():
    config = settings(signing_secret="health-test-framework-signing-key-20260926")
    backend = KafkaBackend("health-test", config, MessageCodec(config))
    # 不启动 broker：发送器保持真实 SDK 对象，只替换网络发现这一边界。
    producer = AIOKafkaProducer()
    backend.producer = producer
    backend.admin = SimpleNamespace(describe_cluster=AsyncMock(return_value={"brokers": [1]}))
    backend.receiving = True
    sender = producer._sender
    try:
        assert not await backend.check_health()  # 尚未启动发送循环。
        await sender.start()
        await asyncio.sleep(0)
        assert await backend.check_health()
        backend.admin.describe_cluster.return_value = {"brokers": []}
        assert not await backend.check_health()
        backend.admin.describe_cluster.return_value = {"brokers": [1]}
        backend.admin.describe_cluster.side_effect = ConnectionError("test broker unavailable")
        with pytest.raises(ConnectionError):
            await backend.check_health()
        backend.admin.describe_cluster.side_effect = None
        await sender.close()
        assert sender.sender_task.done()
        assert not await backend.check_health()  # 元数据成功不能掩盖发送任务停止。
    finally:
        await producer.stop()


@pytest.mark.parametrize("broken", ["connection", "publisher", "consumer"])
async def test_rabbit_checks_connection_and_all_open_channels(broken):
    backend = RabbitBackend("health-test", settings())
    backend.receiving = True
    connected = asyncio.Event()
    connected.set()
    backend.connection = SimpleNamespace(is_closed=False, connected=connected)
    backend.publisher = SimpleNamespace(is_initialized=True, is_closed=False)
    channel = SimpleNamespace(is_initialized=True, is_closed=False)
    backend.channels.append(channel)
    assert await backend.check_health()
    if broken == "connection":
        connected.clear()
    elif broken == "publisher":
        backend.publisher.is_closed = True
    else:
        channel.is_closed = True
    assert not await backend.check_health()
