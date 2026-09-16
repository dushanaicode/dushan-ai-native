import asyncio
import hashlib
from contextvars import Context
from uuid import uuid4

from loguru import logger

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_mq.backend.kafka_backend import KafkaBackend
from framework.starter_mq.backend.rabbit_backend import RabbitBackend
from framework.starter_mq.backend.redis_backend import RedisBackend
from framework.starter_mq.core.consumer_runner import ConsumerRunner
from framework.starter_mq.core.message_codec import MessageCodec
from framework.starter_mq.core.mq_sdk_log_filter import MQSdkLogFilter
from framework.starter_mq.core.replay_store import ReplayStore
from framework.starter_mq.enums.mq_backend import MQBackend
from framework.starter_mq.exception.mq_exception import MQException


class MQRuntime:
    """连接、读循环和有界在途任务全部归属于当前应用。"""

    def __init__(
        self,
        settings,
        application,
        registry,
        cache,
        security,
        tenant,
        database,
        monitor,
        records,
        interceptors,
    ):
        self.settings, self.application, self.registry = settings, application, registry
        self.security, self.tenant, self.database, self.monitor = (
            security,
            tenant,
            database,
            monitor,
        )
        self.records = records
        self.interceptors = sorted(interceptors, key=lambda cls: cls.__mq_interceptor__)
        self.instance = uuid4().hex
        self.codec = MessageCodec(settings)
        client = cache.get_client(settings.cache_key())
        application_key = hashlib.sha256(security.settings.application_id.encode()).hexdigest()[:16]
        broker_prefix = settings.namespace + "." + application_key
        prefix = cache.build_full_key(settings.cache_key(), broker_prefix)
        self.replay = ReplayStore(client, prefix, settings)
        if settings.backend is MQBackend.REDIS:
            self.backend = RedisBackend(client, prefix, settings)
        elif settings.backend is MQBackend.RABBITMQ:
            self.backend = RabbitBackend(broker_prefix, settings)
        else:
            self.backend = KafkaBackend(broker_prefix, settings, self.codec)
        self.runner = ConsumerRunner(self)
        self.log_guard = MQSdkLogFilter()
        self.publish_slots = asyncio.Semaphore(settings.max_concurrency)
        self.phase = "new"
        self.ready = asyncio.Event()
        self.actors = {}
        self.pending = set()
        self.paused = set()
        self.background_error_types = []
        self.completed = self.duplicates = self.rejected = self.observation_failures = 0
        self.peak_inflight = self.cancelling = 0
        self._start_task = self._close_task = self._quiesce_task = None

    async def call(self, awaitable):
        with self.log_guard.quiet():
            async with asyncio.timeout(self.settings.command_timeout_seconds):
                return await awaitable

    async def open(self):
        self.phase = "starting"
        self.log_guard.open()
        definitions = [handler.__mq_consumer__ for handler in self.registry.active()]
        await self.call(self.backend.open(definitions))
        self._start_task = asyncio.create_task(self._start(), context=Context(), name="mq-start")

    async def _start(self):
        try:
            await self.application.wait_until_ready()
            for handler in self.registry.active():
                key = handler.__mq_consumer__.key
                self.actors[key] = asyncio.create_task(
                    self._consume(handler), context=Context(), name="mq:" + key
                )
            await self.call(
                asyncio.gather(*(event.wait() for event in self.backend.ready.values()))
            )
            if self.phase == "starting":
                self.phase = "ready"
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.phase = "failed"
            self.background_error_types.append(type(error).__name__)
            logger.error("MQ 消费启动失败 error_type={}", type(error).__name__)
        finally:
            self.ready.set()

    async def wait_ready(self):
        await self.call(self.ready.wait())
        if self.phase != "ready":
            raise MQException("closed")

    async def _consume(self, handler):
        key = handler.__mq_consumer__.key
        _, concurrency, prefetch = self.registry.limits[key]
        slots = asyncio.Semaphore(concurrency)
        buffer = asyncio.Semaphore(prefetch)
        stream = self.backend.messages(handler.__mq_consumer__, prefetch)
        try:
            while self.phase in {"starting", "ready"} and key not in self.paused:
                await buffer.acquire()
                try:
                    with self.log_guard.quiet():
                        delivery = await anext(stream)
                except BaseException:
                    buffer.release()
                    raise
                if self.application.state is not ApplicationStateEnum.READY:
                    await self.call(delivery.release())
                    buffer.release()
                    break
                task = self.application.tasks.create_task(
                    self._process, handler, delivery, slots, name="mq-delivery:" + key
                )
                self.pending.add(task)
                self.peak_inflight = max(self.peak_inflight, len(self.pending))
                task.add_done_callback(lambda finished: self._finished(finished, buffer))
        except asyncio.CancelledError:
            pass
        except StopAsyncIteration:
            if self.phase in {"starting", "ready"} and self._quiesce_task is None:
                self.paused.add(key)
                logger.error("MQ 接收连接已结束 key={}", key)
        except Exception as error:
            self.paused.add(key)
            self.background_error_types.append(type(error).__name__)
            logger.error("MQ 接收已停止 key={} error_type={}", key, type(error).__name__)
        finally:
            with self.log_guard.quiet():
                await stream.aclose()

    def _finished(self, task, buffer):
        self.pending.discard(task)
        # 任务（包含 DI 收尾）真正结束后才归还预取名额。
        buffer.release()
        if not task.cancelled() and task.exception() is not None:
            error = task.exception()
            self.background_error_types.append(type(error).__name__)
            logger.error("MQ 在途任务失败 error_type={}", type(error).__name__)

    async def _process(self, handler, delivery, slots):
        key = handler.__mq_consumer__.key
        try:
            async with slots:
                result = await self.runner.run(handler, delivery)
            if result == "halt":
                self.paused.add(key)
                self.actors[key].cancel()
            elif result == "busy":
                await asyncio.sleep(self.settings.poll_seconds)
        except asyncio.CancelledError:
            await AsyncioUtils.run_cancellation_shielded(
                self.call(delivery.release()), propagate_cancellation=False
            )
        except Exception as error:
            self.paused.add(key)
            self.actors[key].cancel()
            self.background_error_types.append(type(error).__name__)
            logger.error("MQ 消费已停止 key={} error_type={}", key, type(error).__name__)
            await self.call(delivery.release())

    async def close(self):
        if self._close_task is None:
            self._close_task = asyncio.create_task(
                self._close(), context=Context(), name="mq-close"
            )
        await asyncio.shield(self._close_task)

    async def _close(self):
        self.phase = "closing"
        self.ready.set()
        errors = []
        try:
            await self.quiesce()
        except Exception as error:
            errors.append(error)
        try:
            with self.log_guard.quiet():
                await self.backend.close()
        except Exception as error:
            errors.append(error)
        finally:
            self.log_guard.close()
        self.phase = "closed"
        if errors:
            raise ExceptionGroup("MQ 关闭失败", errors)

    async def quiesce(self):
        """宿主 drain 前停止接收；保留发布连接供现有业务提交后动作使用。"""
        if self._quiesce_task is None:
            self._quiesce_task = asyncio.create_task(
                self._quiesce(), context=Context(), name="mq-quiesce"
            )
        await asyncio.shield(self._quiesce_task)

    async def _quiesce(self):
        errors = []
        if self._start_task is not None:
            self._start_task.cancel()
            await asyncio.gather(self._start_task, return_exceptions=True)
        try:
            await self.call(self.backend.stop_receiving())
        except Exception as error:
            errors.append(error)
        for actor in self.actors.values():
            actor.cancel()
        for result in await asyncio.gather(*self.actors.values(), return_exceptions=True):
            if isinstance(result, Exception):
                errors.append(result)
        if self.pending:
            _, pending = await asyncio.wait(self.pending, timeout=self.settings.shutdown_seconds)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tuple(self.pending), return_exceptions=True)
        if errors:
            raise ExceptionGroup("MQ 停止接收失败", errors)

    def resources(self):
        return {
            "state": self.phase,
            "inflight": len(self.pending),
            "peak_inflight": self.peak_inflight,
            "cancelling": self.cancelling,
            "active_consumers": sum(not task.done() for task in self.actors.values()),
            "paused_consumers": tuple(sorted(self.paused)),
            "completed": self.completed,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "observation_failures": self.observation_failures,
            "background_error_types": tuple(self.background_error_types[-16:]),
        }
