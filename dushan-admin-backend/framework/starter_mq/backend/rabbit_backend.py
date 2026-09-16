import asyncio
import hashlib
import math
import ssl

import aio_pika
from aio_pika.exceptions import DeliveryError
from pamqp.commands import Basic

from framework.starter_mq.backend.message_backend import MessageBackend
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.delivery import Delivery

MINIMUM_BROKER_VERSION = (4, 2, 9)
"""quorum 队列的 x-delivery-limit 负值语义在此版本才被 Broker 端显式转换为"无限制"；
更早版本（例如 3.12.1）把 -1 当作原始上限，首次 nack-requeue 即判定超限静默丢弃，
且不产生任何错误日志。低于该版本的部署在连接建立时即拒绝，不静默接受。"""


class RabbitBackend(MessageBackend):
    """持久 quorum 队列；重试通过 TTL/DLX 确认转移，不占业务执行槽。

    仅支持已验证正确处理 x-delivery-limit 负值语义的 Broker 版本；低于
    MINIMUM_BROKER_VERSION 的部署在 open() 建立连接后立即拒绝并关闭连接。
    """

    def __init__(self, prefix, settings):
        self.prefix, self.settings = prefix, settings
        self.connection = None
        self.publisher = None
        self.receiving = False
        self.queues = {}
        self.iterators = []
        self.channels = []
        self.ready = {}

    def queue(self, destination):
        return self.prefix + "." + destination

    def dlq(self, definition):
        return self.prefix + ".dlq." + definition.key

    def _arguments(self, limit):
        return {
            "x-queue-type": "quorum",
            "x-max-length": limit,
            "x-overflow": "reject-publish",
            "x-delivery-limit": -1,
        }

    @staticmethod
    def _parse_version(raw):
        """解析形如 "4.2.9" 的版本字符串；忽略数字前缀之后的构建/预发布标签。"""
        parts = []
        for segment in str(raw).split(".")[:3]:
            digits = ""
            for character in segment:
                if not character.isdigit():
                    break
                digits += character
            parts.append(int(digits) if digits else 0)
        parts.extend([0] * (3 - len(parts)))
        return tuple(parts)

    def _check_broker_version(self, properties):
        product = properties.get("product") if isinstance(properties, dict) else None
        version = properties.get("version") if isinstance(properties, dict) else None
        if not isinstance(product, str) or "rabbitmq" not in product.lower():
            raise MQException("configuration")
        if not isinstance(version, str) or self._parse_version(version) < MINIMUM_BROKER_VERSION:
            raise MQException("configuration")

    async def _declare(self, name, arguments):
        if name not in self.queues:
            self.queues[name] = await self.publisher.declare_queue(
                name,
                durable=True,
                arguments=arguments,
                timeout=self.settings.command_timeout_seconds,
            )
        return self.queues[name]

    async def open(self, definitions):
        self.ready = {definition.key: asyncio.Event() for definition in definitions}
        tls = None
        if self.settings.rabbit_url.get_secret_value().startswith("amqps://"):
            tls = ssl.create_default_context(cafile=self.settings.rabbit_ca_file)
        connection = await aio_pika.connect(
            self.settings.rabbit_url.get_secret_value(),
            ssl_context=tls,
            timeout=self.settings.command_timeout_seconds,
        )
        try:
            self._check_broker_version(connection.transport.connection.server_properties)
        except MQException:
            await connection.close()
            raise
        self.connection = connection
        self.publisher = await self.connection.channel(
            publisher_confirms=True, on_return_raises=True
        )
        for definition in definitions:
            await self._declare(
                self.queue(definition.destination), self._arguments(self.settings.stream_max_length)
            )
        self.receiving = True

    async def _send(self, name, body):
        try:
            receipt = await self.publisher.default_exchange.publish(
                aio_pika.Message(
                    body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=name,
                mandatory=True,
                timeout=self.settings.command_timeout_seconds,
            )
        except DeliveryError as error:
            raise MQException("confirmation", cause=error) from error
        if not isinstance(receipt, Basic.Ack):
            raise MQException("confirmation")
        return "publisher_confirm", str(receipt.delivery_tag)

    async def publish(self, destination, mode, body):
        name = self.queue(destination)
        await self._declare(name, self._arguments(self.settings.stream_max_length))
        return await self._send(name, body)

    async def retry(self, definition, envelope, body):
        delay = math.ceil(definition.retry.delay(envelope.attempt) * 1000)
        # 每一重试层独立 TTL，避免不同延迟在同一队列产生头阻塞。
        name = (
            self.prefix
            + ".retry."
            + hashlib.sha256(definition.key.encode()).hexdigest()[:24]
            + f".{envelope.attempt}"
        )
        arguments = self._arguments(self.settings.retry_max_length)
        arguments.update(
            {
                "x-message-ttl": delay,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": self.queue(definition.destination),
                "x-dead-letter-strategy": "at-least-once",
            }
        )
        await self._declare(name, arguments)
        await self._send(name, body)

    async def dead_letter(self, definition, body):
        arguments = self._arguments(self.settings.dead_letter_max_length)
        arguments["x-message-ttl"] = self.settings.dead_letter_retention_seconds * 1000
        name = self.dlq(definition)
        await self._declare(name, arguments)
        await self._send(name, body)

    async def messages(self, definition, prefetch):
        channel = await self.connection.channel(publisher_confirms=True)
        self.channels.append(channel)
        await channel.set_qos(prefetch_count=prefetch)
        queue = await channel.declare_queue(
            self.queue(definition.destination),
            durable=True,
            arguments=self._arguments(self.settings.stream_max_length),
        )
        iterator = queue.iterator(no_ack=False)
        self.iterators.append(iterator)
        try:
            async with iterator:
                self.ready[definition.key].set()
                async for incoming in iterator:
                    if not self.receiving:
                        break
                    yield Delivery(
                        incoming.body,
                        str(incoming.delivery_tag),
                        bool(incoming.headers.get("x-death")),
                        incoming.ack,
                        lambda message=incoming: message.nack(requeue=True),
                    )
        finally:
            self.iterators.remove(iterator)

    async def stop_receiving(self):
        self.receiving = False
        for iterator in tuple(self.iterators):
            await iterator.close()

    async def close(self):
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
        self.publisher = None
        self.channels.clear()
        self.queues.clear()
