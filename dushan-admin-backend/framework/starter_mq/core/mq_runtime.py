import asyncio
import hashlib
from collections import deque
from contextvars import Context
from uuid import uuid4

from loguru import logger

from framework.common.utils.asyncio_utils import AsyncioUtils
from framework.starter_cache.exception.redis_recovery import RedisRecovery
from framework.starter_di.context.application_state_enum import ApplicationStateEnum
from framework.starter_monitor.spi.monitor_provider import MonitorProvider
from framework.starter_mq.backend.kafka_backend import KafkaBackend
from framework.starter_mq.backend.rabbit_backend import RabbitBackend
from framework.starter_mq.backend.redis_backend import RedisBackend
from framework.starter_mq.core.consumer_runner import ConsumerRunner
from framework.starter_mq.core.message_codec import MessageCodec
from framework.starter_mq.core.mq_sdk_log_filter import MQSdkLogFilter
from framework.starter_mq.core.replay_store import ReplayStore
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.mq_backend import MQBackend
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_security.spi.security_execution_provider import SecurityExecutionProvider
from framework.starter_tenant.spi.tenant_execution_provider import TenantExecutionProvider


class MQRuntime:
    """连接、读循环和有界在途任务全部归属于当前应用。"""

    def __init__(
        self,
        settings,
        application,
        registry,
        cache,
        security: SecurityExecutionProvider,
        tenant: TenantExecutionProvider | None,
        database,
        monitor: MonitorProvider,
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
        application_key = hashlib.sha256(security.application_id.encode()).hexdigest()[:16]
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
        self.background_error_types = deque(maxlen=16)
        self.recovering = {}
        self.reconnect_attempts = {}
        self.completed = self.duplicates = self.rejected = self.observation_failures = 0
        self.peak_inflight = self.cancelling = 0
        self._close_task = self._quiesce_task = None

    @property
    def is_ready(self) -> bool:
        """检查当前订阅和接收任务，不以历史错误或新消息到达作为恢复条件。"""
        return (
            self.phase == "ready"
            and self.application.state is ApplicationStateEnum.READY
            and self.ready.is_set()
            and self._close_task is None
            and self._quiesce_task is None
            and not self.paused
            and self.actors.keys() == self.backend.ready.keys()
            and all(not task.done() for task in self.actors.values())
            and all(event.is_set() for event in self.backend.ready.values())
        )

    async def check_health(self) -> bool:
        """生产者模式也检查传输；探测沿用命令超时，不发布业务消息。"""
        if not self.is_ready:
            return False
        connected = await self.call(self.backend.check_health())
        return connected and self.is_ready

    async def call(self, awaitable):
        with self.log_guard.quiet():
            async with asyncio.timeout(self.settings.command_timeout_seconds):
                return await awaitable

    async def open(self):
        self.phase = "starting"
        logger.info("【MQStarter】开始初始化消息传输：{}", self.settings.backend.value)
        self.log_guard.open()
        definitions = [handler.__mq_consumer__ for handler in self.registry.active()]
        await self.call(self.backend.open(definitions))
        logger.info("【MQStarter】传输资源初始化完成，等待宿主激活消费者")

    async def activate(self):
        """等待订阅就绪或接收失败，结果直接返回宿主，不以后台启动掩盖失败。"""
        if self.phase != "starting" or self.application.state is not ApplicationStateEnum.READY:
            raise MQException(MQErrorCodes.CLOSED)
        self._activation_failure = asyncio.get_running_loop().create_future()
        subscriptions = asyncio.gather(*(event.wait() for event in self.backend.ready.values()))
        try:
            logger.info("【MQStarter】开始激活消费者，等待全部订阅就绪")
            for handler in self.registry.active():
                key = handler.__mq_consumer__.key
                self.actors[key] = asyncio.create_task(
                    self._consume(handler), context=Context(), name="mq:" + key
                )
            await self.call(
                asyncio.wait(
                    (subscriptions, self._activation_failure), return_when=asyncio.FIRST_COMPLETED
                )
            )
            if self._activation_failure.done():
                raise self._activation_failure.result()
            if (
                self.phase != "starting"
                or self.paused
                or any(task.done() for task in self.actors.values())
            ):
                raise MQException(MQErrorCodes.CLOSED)
            self.phase = "ready"
            logger.info("【MQStarter】激活完成：{} 个消费者接收循环已就绪", len(self.actors))
        except BaseException as error:
            self.phase = "failed"
            if isinstance(error, Exception):
                self.background_error_types.append(type(error).__name__)
            raise
        finally:
            subscriptions.cancel()
            await asyncio.gather(subscriptions, return_exceptions=True)
            self._activation_failure.cancel()
            self.ready.set()

    async def wait_ready(self):
        try:
            await self.call(self.ready.wait())
        except TimeoutError as error:
            raise MQException(MQErrorCodes.CLOSED, cause=error) from error
        if self.phase != "ready":
            raise MQException(MQErrorCodes.CLOSED)

    async def _consume(self, handler):
        key = handler.__mq_consumer__.key
        _, concurrency, prefetch = self.registry.limits[key]
        slots = asyncio.Semaphore(concurrency)
        buffer = asyncio.Semaphore(prefetch)
        delay = self.settings.reconnect_initial_seconds
        while (
            self.phase in {"starting", "ready"}
            and key not in self.paused
            and self._quiesce_task is None
        ):
            stream, failure, cancelled = None, None, False
            try:
                if key in self.recovering and isinstance(self.backend, RedisBackend):
                    await self.call(self.backend.recover_consumer(handler.__mq_consumer__))
                stream = self.backend.messages(handler.__mq_consumer__, prefetch)
                while (
                    self.phase in {"starting", "ready"}
                    and key not in self.paused
                    and self._quiesce_task is None
                ):
                    await buffer.acquire()
                    try:
                        with self.log_guard.quiet():
                            delivery = await anext(stream)
                    except BaseException:
                        buffer.release()
                        raise
                    self.recovering.pop(key, None)
                    delay = self.settings.reconnect_initial_seconds
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
                cancelled = True
            except StopAsyncIteration:
                failure = ConnectionError("消息接收连接已结束")
            except Exception as error:
                failure = error
            finally:
                if stream is not None:
                    try:
                        await self.call(stream.aclose())
                    except Exception as error:
                        failure = (
                            error
                            if failure is None
                            else ExceptionGroup("接收与清理失败", [failure, error])
                        )
            if (
                cancelled
                or self._quiesce_task is not None
                or self.phase not in {"starting", "ready"}
            ):
                if failure is not None and not RedisRecovery.retryable(failure):
                    raise failure
                return
            if failure is None:
                return
            if self.phase == "starting":
                self.paused.add(key)
                if not self._activation_failure.done():
                    self._activation_failure.set_result(failure)
                return
            self.background_error_types.append(type(failure).__name__)
            if not RedisRecovery.retryable(failure):
                self.paused.add(key)
                logger.error("MQ 接收已停止 key={} error_type={}", key, type(failure).__name__)
                return
            self.recovering[key] = type(failure).__name__
            self.backend.ready[key].clear()
            self.reconnect_attempts[key] = self.reconnect_attempts.get(key, 0) + 1
            attempts = self.reconnect_attempts[key]
            if attempts == 1 or attempts % self.settings.reconnect_alert_after == 0:
                logger.log(
                    "ERROR" if attempts >= self.settings.reconnect_alert_after else "WARNING",
                    "MQ 正在恢复 key={} attempt={} delay={} error_type={}",
                    key,
                    attempts,
                    delay,
                    type(failure).__name__,
                )
            await asyncio.sleep(delay)
            delay = min(self.settings.reconnect_max_seconds, delay * 2)

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
            if not RedisRecovery.retryable(error):
                self.paused.add(key)
                self.actors[key].cancel()
            self.background_error_types.append(type(error).__name__)
            logger.error("MQ 消费处理失败 key={} error_type={}", key, type(error).__name__)
            try:
                await self.call(delivery.release())
            except Exception as release_error:
                if not RedisRecovery.retryable(release_error):
                    raise
                self.background_error_types.append(type(release_error).__name__)

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
        recovering = tuple(
            sorted(key for key in self.recovering if not self.backend.ready[key].is_set())
        )
        return {
            "state": "recovering" if self.phase == "ready" and recovering else self.phase,
            "inflight": len(self.pending),
            "peak_inflight": self.peak_inflight,
            "cancelling": self.cancelling,
            "active_consumers": sum(not task.done() for task in self.actors.values()),
            "paused_consumers": tuple(sorted(self.paused)),
            "recovering_consumers": recovering,
            "reconnect_attempts": dict(self.reconnect_attempts),
            "completed": self.completed,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "observation_failures": self.observation_failures,
            "background_error_types": tuple(self.background_error_types),
        }
