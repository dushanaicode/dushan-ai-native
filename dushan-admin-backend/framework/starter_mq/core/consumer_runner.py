import asyncio
import time

from loguru import logger
from pydantic import ValidationError

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_mq.core.consumer_invoker import ConsumerInvoker
from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.enums.message_state import MessageState
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.consume_outcome import ConsumeOutcome
from framework.starter_mq.model.consume_record import ConsumeRecord
from framework.starter_mq.model.message_context import MessageContext
from framework.starter_security.exception.security_exception import SecurityException


class ConsumerRunner:
    """保存业务终态后结算传输，结算重试不会再次调用业务。"""

    def __init__(self, runtime):
        self.runtime = runtime
        self.invoker = ConsumerInvoker(runtime)

    async def authenticate(self, definition, delivery):
        runtime = self.runtime
        if definition.external_authenticator is not None and not delivery.retry:

            async def external():
                provider = runtime.application.container.get(definition.external_authenticator)
                result = await provider.authenticate(
                    delivery.body, destination=definition.destination
                )
                runtime.codec.validate(result, definition.destination, check_age=False)
                return runtime.codec.sign(result)

            envelope = await runtime.call(runtime.application.tasks.run_isolated(external))
        else:
            envelope = runtime.codec.decode(delivery.body, definition.destination, check_age=False)
        if (envelope.attempt == 0 and envelope.consumer_key is not None) or (
            envelope.attempt > 0 and envelope.consumer_key != definition.key
        ):
            raise MQException("authentication")
        return envelope

    async def run(self, handler_type, delivery):
        runtime = self.runtime
        definition = handler_type.__mq_consumer__
        started = time.monotonic()
        try:
            envelope = await self.authenticate(definition, delivery)
        except Exception as error:
            rejected = (
                isinstance(error, ValidationError)
                or (
                    isinstance(error, MQException)
                    and error.reason in {"invalid", "authentication", "expired"}
                )
                or (
                    isinstance(error, SecurityException)
                    and error.reason not in {"unavailable", "configuration", "closed"}
                )
            )
            if not rejected:
                raise
            runtime.rejected += 1
            logger.warning(
                "MQ 消息认证拒绝 key={} error_type={}", definition.key, type(error).__name__
            )
            await runtime.call(delivery.acknowledge())
            return "settled"
        context = MessageContext(
            envelope.message_id,
            definition.key,
            definition.destination,
            envelope.attempt,
            envelope.tenant_id,
        )
        if envelope.ready_at > time.time():
            await runtime.call(delivery.release())
            return "busy"
        instance = runtime.instance if definition.mode is MessageMode.PUBSUB else None
        key = runtime.replay.key(definition, envelope, instance=instance)
        lock = runtime.replay.lock(key)
        if not await lock.acquire():
            await runtime.call(delivery.release())
            return "busy"
        lease_lost = asyncio.Event()
        heartbeat = asyncio.create_task(self._renew(lock, lease_lost))
        outcome = None
        observation_errors = []
        result = "settled"
        try:
            record = await runtime.call(runtime.replay.read(key))
            digest = runtime.codec.digest(envelope)
            if record is not None and record["digest"] != digest:
                raise MQException("conflict")
            if record is not None and (
                record["stage"] == "done" or envelope.attempt < record["attempt"]
            ):
                await runtime.call(delivery.acknowledge())
                runtime.duplicates += 1
                return "settled"
            if record is not None and envelope.attempt > record["attempt"]:
                raise MQException("conflict")
            if record is not None and record["stage"] == "settle":
                result = await self._settle(definition, envelope, delivery, key, lock, record)
                return result
            if (record is not None and record["stage"] == "executing") or (
                record is None and envelope.attempt
            ):
                outcome = ConsumeOutcome(MessageState.UNKNOWN, MQException("unknown"))
            elif envelope.expires_at < time.time() - runtime.settings.clock_skew_seconds:
                outcome = ConsumeOutcome(MessageState.REJECTED, MQException("expired"))
            else:
                record = {"digest": digest, "stage": "executing", "attempt": envelope.attempt}
                await runtime.call(runtime.replay.write(key, lock, record))
                outcome = await self.invoker.invoke(
                    handler_type, envelope, context, lease_lost, lock
                )
            observation_errors.extend(outcome.observation_errors)
            if outcome.state is MessageState.CANCELLED:
                await runtime.call(
                    runtime.replay.write(
                        key, lock, {"digest": digest, "stage": "ready", "attempt": envelope.attempt}
                    )
                )
                await runtime.call(delivery.release())
                return "settled"
            record = self._terminal(definition, envelope, digest, outcome)
            await runtime.call(runtime.replay.write(key, lock, record))
            result = await AsyncioUtils.run_cancellation_shielded(
                self._settle(definition, envelope, delivery, key, lock, record),
                propagate_cancellation=False,
            )
        except asyncio.CancelledError:
            await AsyncioUtils.run_cancellation_shielded(
                delivery.release(), propagate_cancellation=False
            )
            raise
        except Exception as error:
            observation_errors.append(error)
            logger.error("MQ 结算停止 key={} error_type={}", definition.key, type(error).__name__)
            # 终态留在 Redis；重启后只补结算，绝不由异常触发业务重执。
            await runtime.call(delivery.release())
            result = "halt"
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            if lock.release_required:
                try:
                    await lock.release()
                except Exception as error:
                    observation_errors.append(error)
            if outcome is not None:
                await self._record(
                    ConsumeRecord(
                        context,
                        outcome.state,
                        time.monotonic() - started,
                        type(outcome.error).__name__ if outcome.error else None,
                        tuple(type(error).__name__ for error in observation_errors),
                    )
                )
        return result

    def _terminal(self, definition, envelope, digest, outcome):
        state = outcome.state
        if state is MessageState.RETRY and envelope.attempt < definition.retry.count:
            delay = definition.retry.delay(envelope.attempt + 1)
            ready = time.time() + delay
            if ready < envelope.expires_at:
                return {
                    "digest": digest,
                    "stage": "settle",
                    "attempt": envelope.attempt,
                    "action": "retry",
                    "ready_at": ready,
                    "state": state.value,
                    "error_type": type(outcome.error).__name__,
                }
        action = "ack" if state is MessageState.SUCCEEDED else definition.exhausted.value
        return {
            "digest": digest,
            "stage": "settle",
            "attempt": envelope.attempt,
            "action": action,
            "state": state.value,
            "error_type": type(outcome.error).__name__ if outcome.error else None,
        }

    async def _settle(self, definition, envelope, delivery, key, lock, record):
        runtime = self.runtime
        action = record["action"]
        if action == "hold":
            logger.error("MQ 消息保留未确认 key={} state={}", definition.key, record["state"])
            return "halt"
        if action == "retry":
            retry = runtime.codec.sign(
                envelope.model_copy(
                    update={
                        "attempt": envelope.attempt + 1,
                        "ready_at": record["ready_at"],
                        "consumer_key": definition.key,
                    }
                )
            )
            await runtime.call(
                runtime.backend.retry(definition, retry, runtime.codec.encode(retry))
            )
            saved = {"digest": record["digest"], "stage": "ready", "attempt": retry.attempt}
        else:
            if action == "dead_letter":
                body = runtime.codec.canonical(
                    {
                        "consumer_key": definition.key,
                        "message_id": envelope.message_id,
                        "state": record["state"],
                        "attempt": envelope.attempt,
                        "error_type": record["error_type"],
                        "replayable": record["state"] != MessageState.UNKNOWN.value,
                        "envelope": None
                        if record["state"] == MessageState.UNKNOWN.value
                        else envelope.model_dump(),
                    }
                )
                await runtime.call(runtime.backend.dead_letter(definition, body))
            elif action == "discard":
                logger.warning(
                    "MQ 消息已按声明丢弃 key={} state={}", definition.key, record["state"]
                )
            saved = {"digest": record["digest"], "stage": "done", "attempt": envelope.attempt}
        await runtime.call(runtime.replay.write(key, lock, saved))
        await runtime.call(delivery.acknowledge())
        return "settled"

    async def _renew(self, lock, lease_lost):
        try:
            while True:
                await asyncio.sleep(self.runtime.settings.renew_seconds)
                if not await lock.renew():
                    lease_lost.set()
                    return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error("MQ 消费续租失败 error_type={}", type(error).__name__)
            lease_lost.set()

    async def _record(self, record):
        runtime = self.runtime
        runtime.completed += 1
        runtime.observation_failures += len(record.observation_error_types)
        if runtime.records is not None:
            try:
                await runtime.call(
                    runtime.application.tasks.run_isolated(lambda: runtime.records.append(record))
                )
            except Exception as error:
                runtime.observation_failures += 1
                logger.error("MQ 消费观测失败 error_type={}", type(error).__name__)
