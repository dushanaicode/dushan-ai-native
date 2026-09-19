import asyncio
import hashlib
import ssl
import time

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError, for_code
from aiokafka.structs import TopicPartition

from framework.starter_mq.backend.kafka_assignments import KafkaAssignments
from framework.starter_mq.backend.message_backend import MessageBackend
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.delivery import Delivery


class KafkaBackend(MessageBackend):
    """同一分区只持有一条未结算消息；重试主题到期前暂停该分区。"""

    def __init__(self, prefix, settings, codec):
        self.prefix, self.settings, self.codec = prefix, settings, codec
        self.producer = None
        self.admin = None
        self.consumers = []
        self.topics = set()
        self.receiving = False
        self.ready = {}

    def topic(self, destination):
        return self.prefix + "." + hashlib.sha256(destination.encode()).hexdigest()[:32]

    def retry_topic(self, definition):
        return self.topic("retry:" + definition.key)

    def dlq(self, definition):
        return self.topic("dlq:" + definition.key)

    def connection_options(self):
        settings = self.settings
        options = {
            "bootstrap_servers": settings.kafka_bootstrap_servers,
            "security_protocol": settings.kafka_security_protocol,
            "request_timeout_ms": int(settings.command_timeout_seconds * 1000),
        }
        if "SSL" in settings.kafka_security_protocol:
            context = ssl.create_default_context(cafile=settings.kafka_ca_file)
            if settings.kafka_cert_file is not None:
                context.load_cert_chain(settings.kafka_cert_file, settings.kafka_key_file)
            options["ssl_context"] = context
        if settings.kafka_sasl_mechanism is not None:
            options.update(
                sasl_mechanism=settings.kafka_sasl_mechanism,
                sasl_plain_username=settings.kafka_sasl_username,
                sasl_plain_password=settings.kafka_sasl_password.get_secret_value(),
            )
        return options

    async def _declare(self, name, *, dead_letter=False):
        if name in self.topics:
            return
        retention = (
            self.settings.dead_letter_retention_seconds
            if dead_letter
            else self.settings.max_age_seconds
        )
        request = NewTopic(
            name,
            self.settings.kafka_partitions,
            self.settings.kafka_replication_factor,
            topic_configs={
                "cleanup.policy": "delete",
                "retention.ms": str(retention * 1000),
                "retention.bytes": str(self.settings.kafka_retention_bytes),
                "max.message.bytes": str(self.codec.wire_limit),
                "segment.bytes": str(max(1048576, self.codec.wire_limit)),
            },
        )
        result = await self.admin.create_topics([request])
        for item in result.topic_errors:
            error_code = item[1]
            if error_code and for_code(error_code) is not TopicAlreadyExistsError:
                raise MQException(MQErrorCodes.CONFIRMATION, cause=for_code(error_code)())
        # CreateTopics 已确认后，Broker 的 metadata 视图仍可能短暂返回主题/leader 未就绪。
        deadline = asyncio.get_running_loop().time() + self.settings.command_timeout_seconds
        while True:
            metadata = await self.admin.describe_topics([name])
            if metadata and metadata[0]["error_code"] == 0:
                break
            if metadata and metadata[0]["error_code"] not in {3, 5}:
                raise MQException(
                    MQErrorCodes.CONFIRMATION, cause=for_code(metadata[0]["error_code"])()
                )
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise MQException(MQErrorCodes.CONFIRMATION)
            await asyncio.sleep(min(remaining, self.settings.poll_seconds))
        if (
            len(metadata) != 1
            or metadata[0]["error_code"] != 0
            or len(metadata[0]["partitions"]) != self.settings.kafka_partitions
        ):
            raise MQException(MQErrorCodes.CONFIGURATION)
        self.topics.add(name)

    async def open(self, definitions):
        self.ready = {definition.key: asyncio.Event() for definition in definitions}
        options = self.connection_options()
        self.admin = AIOKafkaAdminClient(**options)
        await self.admin.start()
        for definition in definitions:
            await self._declare(self.topic(definition.destination))
            await self._declare(self.retry_topic(definition))
        self.producer = AIOKafkaProducer(
            **options,
            acks="all",
            enable_idempotence=True,
            max_request_size=self.codec.wire_limit,
            max_batch_size=self.codec.wire_limit,
        )
        await self.producer.start()
        self.receiving = True

    async def _send(self, name, body, key=None):
        result = await self.producer.send_and_wait(name, body, key=key)
        return "partition_offset", f"{result.partition}:{result.offset}"

    async def publish(self, destination, mode, body):
        name = self.topic(destination)
        await self._declare(name)
        return await self._send(name, body)

    async def retry(self, definition, envelope, body):
        await self._send(self.retry_topic(definition), body, envelope.message_id.encode())

    async def dead_letter(self, definition, body):
        name = self.dlq(definition)
        await self._declare(name, dead_letter=True)
        await self._send(name, body)

    async def messages(self, definition, prefetch):
        options = self.connection_options()
        consumer = AIOKafkaConsumer(
            **options,
            group_id=self.prefix + "." + definition.group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_records=1,
            fetch_max_bytes=self.codec.wire_limit * prefetch,
            max_partition_fetch_bytes=self.codec.wire_limit,
            max_poll_interval_ms=max(
                300000,
                int(
                    (self.settings.handler_timeout_seconds + self.settings.shutdown_seconds) * 2000
                ),
            ),
        )
        self.consumers.append(consumer)
        assignments = KafkaAssignments(prefetch)
        consumer.subscribe(
            [self.topic(definition.destination), self.retry_topic(definition)], listener=assignments
        )
        await consumer.start()
        deferred = {}
        while self.receiving:
            if consumer.assignment():
                self.ready[definition.key].set()
            if assignments.exceeded:
                raise MQException(MQErrorCodes.CONFIGURATION)
            now = time.time()
            for partition, (record, ready_at, version) in tuple(deferred.items()):
                if version != assignments.version:
                    del deferred[partition]
                elif ready_at <= now:
                    del deferred[partition]
                    yield self._delivery(consumer, assignments, definition, record, version)
            assignment = consumer.assignment()
            available = assignment - consumer.paused()
            if assignment and not available:
                await asyncio.sleep(self.settings.poll_seconds)
                continue
            # 显式排除暂停分区，否则 aiokafka 会清空它们已预取的剩余记录。
            batches = await consumer.getmany(
                *available, timeout_ms=max(1, int(self.settings.poll_seconds * 1000)), max_records=1
            )
            for partition, records in batches.items():
                consumer.pause(partition)
                record = records[0]
                version = assignments.version
                ready_at = now
                if record.topic == self.retry_topic(definition):
                    try:
                        envelope = self.codec.decode(
                            record.value, definition.destination, check_age=False
                        )
                        ready_at = envelope.ready_at
                    except MQException:
                        # 非法消息立即交认证拒绝路径，不能用伪造时间永久堵住分区。
                        pass
                if ready_at > time.time():
                    deferred[partition] = (record, ready_at, version)
                else:
                    yield self._delivery(consumer, assignments, definition, record, version)

    def _delivery(self, consumer, assignments, definition, record, version):
        partition = TopicPartition(record.topic, record.partition)

        def require_assignment():
            if version != assignments.version or partition not in consumer.assignment():
                raise MQException(MQErrorCodes.LEASE)

        async def acknowledge():
            require_assignment()
            await consumer.commit({partition: record.offset + 1})
            require_assignment()
            consumer.resume(partition)

        async def release():
            require_assignment()
            consumer.seek(partition, record.offset)
            consumer.resume(partition)

        return Delivery(
            record.value,
            f"{record.partition}:{record.offset}",
            record.topic == self.retry_topic(definition),
            acknowledge,
            release,
        )

    async def stop_receiving(self):
        self.receiving = False

    async def close(self):
        self.receiving = False
        errors = []
        for client in (*self.consumers, self.producer):
            if client is not None:
                try:
                    await client.stop()
                except Exception as error:
                    errors.append(error)
        if self.admin is not None:
            try:
                await self.admin.close()
            except Exception as error:
                errors.append(error)
        self.consumers.clear()
        self.producer = self.admin = None
        if errors:
            raise ExceptionGroup("Kafka 连接关闭失败", errors)
