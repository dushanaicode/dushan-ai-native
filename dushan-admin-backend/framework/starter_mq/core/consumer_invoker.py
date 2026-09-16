import asyncio

from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic import ValidationError

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_mq.enums.message_state import MessageState
from framework.starter_mq.enums.tenant_policy import TenantPolicy
from framework.starter_mq.exception.message_rejected import MessageRejected
from framework.starter_mq.exception.message_result_unknown import MessageResultUnknown
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.consume_outcome import ConsumeOutcome
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_tenant.exception.tenant_exception import TenantException


class ConsumerInvoker:
    """一次消息一个新的 Security/DI 执行；业务终态与拦截器清理错误分离。"""

    def __init__(self, runtime):
        self.runtime = runtime

    async def invoke(self, handler_type, envelope, context, lease_lost, lock):
        task = asyncio.create_task(self._authenticated(handler_type, envelope, context, lock))
        lost = asyncio.create_task(lease_lost.wait())
        interruption = None
        try:
            completed, _ = await asyncio.wait(
                {task, lost},
                timeout=self.runtime.settings.handler_timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if task in completed:
                return self._result(task)
            interruption = MQException("lease") if lost in completed else TimeoutError()
        except asyncio.CancelledError as error:
            interruption = error
        finally:
            lost.cancel()
            await asyncio.gather(lost, return_exceptions=True)
        task.cancel()
        # 不在业务还运行时释放租约或依赖。抗取消任务继续占用原来的有界槽。
        self.runtime.cancelling += 1
        try:
            await AsyncioUtils.run_cancellation_shielded(
                asyncio.gather(task, return_exceptions=True), propagate_cancellation=False
            )
        finally:
            self.runtime.cancelling -= 1
        if isinstance(interruption, MQException):
            return ConsumeOutcome(MessageState.UNKNOWN, interruption)
        if not task.cancelled():
            outcome = self._result(task)
            if outcome.state is MessageState.SUCCEEDED:
                return outcome
        state = (
            MessageState.CANCELLED
            if isinstance(interruption, asyncio.CancelledError)
            else MessageState.UNKNOWN
        )
        return ConsumeOutcome(state, interruption)

    @staticmethod
    def _result(task):
        if task.cancelled():
            return ConsumeOutcome(MessageState.CANCELLED, asyncio.CancelledError())
        error = task.exception()
        if error is None:
            return task.result()
        if isinstance(error, (AfterCommitException, MessageResultUnknown)):
            return ConsumeOutcome(MessageState.UNKNOWN, error)
        if isinstance(error, SecurityException) and error.reason in {
            "unavailable",
            "configuration",
            "closed",
        }:
            return ConsumeOutcome(MessageState.RETRY, error)
        if isinstance(error, TenantException) and error.reason in {"configuration", "closed"}:
            return ConsumeOutcome(MessageState.RETRY, error)
        if isinstance(
            error, (SecurityException, TenantException, MessageRejected, ValidationError)
        ):
            return ConsumeOutcome(MessageState.REJECTED, error)
        return ConsumeOutcome(MessageState.RETRY, error)

    async def _authenticated(self, handler_type, envelope, context, lock):
        runtime = self.runtime
        definition = handler_type.__mq_consumer__
        payload = runtime.codec.payload(envelope)
        proof = runtime.codec.proof(envelope)
        business_outcome = None

        async def execute(raw):
            nonlocal business_outcome
            identity = (
                runtime.security.context.current()
                if envelope.authority == "session"
                else runtime.security.context.current_workload()
            )
            if identity is None or identity.tenant_id != envelope.tenant_id:
                raise MessageRejected()
            if definition.tenant_policy is TenantPolicy.GLOBAL:
                if envelope.tenant_id is not None:
                    raise MessageRejected()
            else:
                if envelope.tenant_id is None or runtime.tenant is None:
                    raise MessageRejected()
                frame = runtime.tenant.context.current()
                if (
                    not frame.available
                    and definition.tenant_policy is not TenantPolicy.ALLOW_UNAVAILABLE
                ):
                    raise MessageRejected()
            message = definition.message.model_validate_json(raw, strict=True, extra="forbid")
            handler = runtime.application.container.get(handler_type)
            if not lock.is_valid:
                raise MessageResultUnknown()
            with runtime.monitor.span(
                "mq.consume",
                {
                    "messaging.destination.name": definition.destination,
                    "messaging.consumer.key": definition.key,
                    "messaging.message.id": context.message_id,
                    "messaging.message.attempt": context.attempt,
                },
                kind=SpanKind.CONSUMER,
                parent=runtime.monitor.extract(envelope.trace_headers),
            ) as span:
                business_outcome = await self._handle(handler, message, context)
                span.set_status(
                    Status(
                        StatusCode.OK
                        if business_outcome.state is MessageState.SUCCEEDED
                        else StatusCode.ERROR
                    )
                )
                return business_outcome

        try:
            if envelope.authority == "session":
                if definition.session_policy is None:
                    raise MessageRejected()
                return await runtime.security.run_message(
                    proof,
                    payload,
                    definition.session_policy,
                    execute,
                    audience=definition.destination,
                )
            if envelope.capability not in definition.workload_capabilities:
                raise MessageRejected()
            return await runtime.security.run_workload_message(
                proof,
                payload,
                execute,
                audience=definition.destination,
                capability=envelope.capability,
            )
        except BaseException as error:
            if business_outcome is None:
                raise
            # Security/Tenant 的退出失败不能抹掉已经取得的业务终态。
            return ConsumeOutcome(
                business_outcome.state,
                business_outcome.error,
                (*business_outcome.observation_errors, error),
            )

    async def _handle(self, handler, message, context):
        managers = []
        primary = None
        cleanup_errors = []
        state = MessageState.SUCCEEDED
        try:
            for interceptor_type in self.runtime.interceptors:
                manager = self.runtime.application.container.get(interceptor_type).enter(context)
                await manager.__aenter__()
                managers.append(manager)
            await handler.handle(message, context)
        except asyncio.CancelledError as error:
            primary, state = error, MessageState.CANCELLED
        except (AfterCommitException, MessageResultUnknown) as error:
            primary, state = error, MessageState.UNKNOWN
        except (MessageRejected, ValidationError) as error:
            primary, state = error, MessageState.REJECTED
        except Exception as error:
            primary, state = error, MessageState.RETRY
        finally:
            for manager in reversed(managers):
                try:
                    await manager.__aexit__(
                        type(primary) if primary else None,
                        primary,
                        primary.__traceback__ if primary else None,
                    )
                except BaseException as error:
                    cleanup_errors.append(error)
        return ConsumeOutcome(state, primary, tuple(cleanup_errors))
