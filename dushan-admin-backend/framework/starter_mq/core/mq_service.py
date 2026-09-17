import asyncio
import base64
import time

from pydantic import BaseModel

from framework.starter_di.decorators.components import framework
from framework.starter_mq.core.backend_capabilities import BackendCapabilities
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.message_envelope import MessageEnvelope
from framework.starter_mq.model.prepared_message import PreparedMessage
from framework.starter_mq.model.publish_receipt import PublishReceipt


@framework
class MQService:
    """业务发布入口；after_commit 不等于最终送达，可靠发布使用 OutboxService。"""

    def __init__(self):
        self.runtime = None
        self.declarations = ()

    def require_runtime(self):
        if self.runtime is None or self.runtime.phase not in {"starting", "ready"}:
            raise MQException("closed")
        return self.runtime

    async def prepare(self, command) -> PreparedMessage:
        runtime = self.require_runtime()
        try:
            BackendCapabilities.for_mode(runtime.settings.backend, command.mode)
        except ValueError as error:
            raise MQException("declaration", cause=error) from error
        if not isinstance(command.message, BaseModel):
            raise MQException("invalid")
        payload = command.message.model_dump_json().encode()
        if len(payload) > runtime.settings.max_message_bytes:
            raise MQException("invalid")
        workload = runtime.security.context.current_workload()
        if workload is not None:
            authority, tenant_id = "workload", workload.tenant_id
            proof = await runtime.security.issue_workload_message(
                payload, audience=command.destination, capability=command.capability
            )
        else:
            if command.capability is not None:
                raise MQException("authentication")
            identity = runtime.security.context.require()
            authority, tenant_id = "session", identity.tenant_id
            proof = await runtime.security.issue_message(payload, audience=command.destination)
        if tenant_id is not None:
            if (
                runtime.tenant is None
                or runtime.tenant.context.get_required_tenant_id() != tenant_id
            ):
                raise MQException("authentication")
        now = time.time()
        envelope = MessageEnvelope(
            version=1,
            message_id=command.id(),
            destination=command.destination,
            authority=authority,
            capability=command.capability,
            tenant_id=tenant_id,
            proof=base64.b64encode(proof).decode(),
            payload=base64.b64encode(payload).decode(),
            issued_at=now,
            expires_at=now + runtime.settings.max_age_seconds,
            attempt=0,
            ready_at=now,
            consumer_key=None,
            trace_headers={
                key: value
                for key, value in runtime.monitor.inject().items()
                if key in {"traceparent", "tracestate"}
            },
            signature="0" * 64,
        )
        runtime.codec.validate(envelope, command.destination)
        return PreparedMessage(mode=command.mode, envelope=runtime.codec.sign(envelope))

    async def publish(self, command) -> PublishReceipt:
        return await self.send_prepared(await self.prepare(command))

    async def send_prepared(self, message) -> PublishReceipt:
        runtime = self.require_runtime()
        await runtime.wait_ready()
        envelope = runtime.codec.decode(
            runtime.codec.encode(message.envelope), message.envelope.destination
        )
        BackendCapabilities.for_mode(runtime.settings.backend, message.mode)
        try:
            async with asyncio.timeout(runtime.settings.command_timeout_seconds):
                await runtime.publish_slots.acquire()
        except TimeoutError as error:
            raise MQException("capacity", cause=error) from error
        try:
            if runtime.phase != "ready":
                raise MQException("closed")
            try:
                confirmation, reference = await runtime.call(
                    runtime.backend.publish(
                        envelope.destination, message.mode, runtime.codec.encode(envelope)
                    )
                )
            except MQException:
                raise
            except asyncio.CancelledError as error:
                error.add_note(
                    "MQ publish was cancelled; broker acceptance may already have occurred"
                )
                raise
            except Exception as error:
                raise MQException("unknown", cause=error) from error
            return PublishReceipt(envelope.message_id, confirmation, reference)
        finally:
            runtime.publish_slots.release()

    async def publish_after_commit(self, command) -> str:
        runtime = self.require_runtime()
        if runtime.database is None:
            raise MQException("configuration")
        prepared = await self.prepare(command)
        runtime.database.after_commit(
            lambda: self.send_prepared(prepared), required=True, name="mq-publish"
        )
        return prepared.envelope.message_id
