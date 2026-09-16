import asyncio
import time
from contextvars import Context
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, ValidationError
from starlette.websockets import WebSocketDisconnect, WebSocketState

from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_logging.context.log_context import LogContext
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.model.online_connection import OnlineConnection
from framework.starter_websocket.model.socket_context import SocketContext
from framework.starter_websocket.model.socket_message import SocketMessage


class SocketConnection:
    """每连接独立读取、处理和串行发送；有界队列直到真实任务结束才释放。"""

    def __init__(self, runtime, websocket, handshake):
        self.runtime, self.websocket = runtime, websocket
        self.id = uuid4().hex
        self.session, self.audience = handshake.session, handshake.audience
        self.allowed_events, self.validated_at = handshake.allowed_events, handshake.validated_at
        self.client_ip, self.language, self.subprotocol = (
            handshake.client_ip,
            handshake.language,
            handshake.subprotocol,
        )
        self.inbound = asyncio.Queue(runtime.settings.inbound_queue_size)
        self.outbound = asyncio.Queue(runtime.settings.outbound_queue_size)
        self.last_activity = time.monotonic()
        self.phase = "new"
        self.reader = self.sender = None
        self.processors = []
        self._close_task = None
        self.closed = asyncio.Event()
        self.close_code = 1000
        self.error = None
        self.peak_inbound = self.peak_outbound = 0
        self.active_handlers = 0

    @property
    def information(self):
        return OnlineConnection(
            client_id=self.id,
            instance=self.runtime.instance,
            audience=self.audience,
            tenant_id=self.session.tenant_id,
            member_id=self.session.membership_id,
        )

    @property
    def current(self):
        return (
            time.monotonic() < self.validated_at + self.runtime.settings.heartbeat_interval_seconds
            and time.time() < self.session.expires_at.timestamp()
            and (self.runtime.online is None or self.runtime.online.valid)
        )

    def enqueue(self, message, *, builtin=False, continuation=False):
        if self.phase != "active" and not (continuation and self.phase == "draining"):
            return False
        if not builtin:
            if not self.current:
                self.request_close(4001)
                return False
            if message.type not in self.allowed_events:
                return False
        self.runtime.codec.encode(message)
        try:
            self.outbound.put_nowait((message, builtin))
        except asyncio.QueueFull:
            self.runtime.slow_connections += 1
            self.request_close(1013)
            return False
        self.peak_outbound = max(self.peak_outbound, self.outbound.qsize())
        return True

    def error_message(self, error, request_id=None):
        code = error.error_code.code if isinstance(error, BaseBusinessException) else 500
        message = (
            error.msg
            if isinstance(error, (SocketException, SecurityException))
            else "WebSocket 消息处理失败"
        )
        if isinstance(error, BaseBusinessException) and error.error_code.message_key:
            message = self.runtime.translator.translate_any_scope(
                error.error_code.message_key, self.language, default=message
            )
        self.enqueue(
            SocketMessage(
                type="error", payload={"code": code, "message": message}, request_id=request_id
            ),
            builtin=True,
            continuation=True,
        )

    async def run(self):
        self.phase = "active"
        self.sender = asyncio.create_task(
            self._send(), context=Context(), name="ws-send:" + self.id
        )
        self.processors = [
            asyncio.create_task(self._process(), context=Context(), name="ws-process:" + self.id)
            for _ in range(self.runtime.settings.handler_concurrency)
        ]
        self.reader = asyncio.create_task(
            self._read(), context=Context(), name="ws-read:" + self.id
        )
        self.enqueue(
            SocketMessage(type="connect", payload={"clientId": self.id, "audience": self.audience}),
            builtin=True,
        )
        try:
            await self.closed.wait()
        except asyncio.CancelledError:
            self.request_close(1001)
            await AsyncioUtils.run_cancellation_shielded(
                self._close_task, propagate_cancellation=False
            )
            raise
        await self._close_task

    async def _read(self):
        try:
            while self.phase == "active":
                event = await self.websocket.receive()
                if event["type"] == "websocket.disconnect":
                    self.request_close(event.get("code", 1000))
                    return
                if "text" not in event:
                    self.request_close(1003, SocketException("protocol"))
                    return
                self.last_activity = time.monotonic()
                try:
                    message = self.runtime.codec.parse(event["text"])
                except SocketException as error:
                    self.error_message(error)
                    if error.reason == "too_large":
                        self.request_close(1009, error)
                        return
                    continue
                if message.type in {"ping", "pong"}:
                    if not self.current:
                        self.request_close(4001)
                        return
                    if message.type == "ping":
                        self.enqueue(
                            SocketMessage(type="pong", request_id=message.request_id), builtin=True
                        )
                    continue
                try:
                    self.inbound.put_nowait(message)
                except asyncio.QueueFull:
                    self.error_message(SocketException("capacity"), message.request_id)
                    self.request_close(1013)
                    return
                self.peak_inbound = max(self.peak_inbound, self.inbound.qsize())
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.request_close(1011, error)

    async def _process(self):
        while True:
            message = await self.inbound.get()
            self.active_handlers += 1
            try:
                handler = self.runtime.registry.handlers.get((self.audience, message.type))
                policy = (
                    self.runtime.registry.audience(self.audience).policy
                    if handler is None
                    else handler.__socket_handler__.policy
                )

                async def execute(session):
                    if message.sender_id is not None and message.sender_id != session.membership_id:
                        raise SocketException("policy")
                    if handler is None:
                        raise SocketException("unknown_type")
                    payload = handler.__socket_handler__.payload.model_validate(
                        message.payload, strict=True, extra="forbid"
                    )
                    context = SocketContext(
                        self, ApplicationContext.current_execution(), message.request_id
                    )
                    token = LogContext.begin_request(message.request_id or uuid4().hex)
                    LogContext.set_client_ip(self.client_ip)
                    try:
                        with logger.contextualize(logging_owner=self.runtime.logging_owner):
                            with self.runtime.monitor.span(
                                "websocket.message",
                                {
                                    "websocket.type": message.type,
                                    "websocket.client_id": self.id,
                                    "websocket.audience": self.audience,
                                },
                            ):
                                await self.runtime.application.container.get(handler).handle(
                                    payload, context
                                )
                    finally:
                        context.active = False
                        LogContext.reset(token)

                async with asyncio.timeout(self.runtime.settings.handler_timeout_seconds):
                    await self.runtime.security.run_session_reference(self.session, policy, execute)
                self.runtime.handled += 1
            except asyncio.CancelledError:
                raise
            except SecurityException as error:
                self.error_message(error, message.request_id)
                if error.reason != "denied":
                    self.request_close(4001, error)
            except ValidationError as error:
                self.error_message(SocketException("protocol", cause=error), message.request_id)
            except Exception as error:
                self.runtime.record_error(error)
                self.error_message(error, message.request_id)
            finally:
                self.active_handlers -= 1
                self.inbound.task_done()

    async def _project(self, message):
        definition = self.runtime.registry.event(self.audience, message.type)
        if definition.projector is None:
            return message

        async def project(session):
            context = SocketContext(
                self, ApplicationContext.current_execution(), message.request_id
            )
            try:
                payload = definition.payload.model_validate(
                    message.payload, strict=True, extra="forbid"
                )
                result = await self.runtime.application.container.get(definition.projector).project(
                    payload, context
                )
                if result is None:
                    return None
                value = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
                checked = self.runtime.registry.event_payload(self.audience, message.type, value)
                return message.model_copy(update={"payload": checked.model_dump(mode="json")})
            finally:
                context.active = False

        async with asyncio.timeout(self.runtime.settings.authorization_timeout_seconds):
            return await self.runtime.security.run_session_reference(
                self.session, definition.policy, project
            )

    async def _send(self):
        try:
            while True:
                message, builtin = await self.outbound.get()
                try:
                    if not builtin:
                        if not self.current or message.type not in self.allowed_events:
                            self.request_close(4001)
                            return
                        message = await self._project(message)
                        if message is None:
                            continue
                    async with asyncio.timeout(self.runtime.settings.send_timeout_seconds):
                        await self.websocket.send_text(self.runtime.codec.encode(message))
                finally:
                    self.outbound.task_done()
        except asyncio.CancelledError:
            raise
        except TimeoutError as error:
            self.runtime.slow_connections += 1
            self.request_close(1013, error)
        except SecurityException as error:
            self.request_close(4001, error)
        except Exception as error:
            self.request_close(1011, error)

    def request_close(self, code, error=None):
        if self._close_task is not None:
            return self._close_task
        self.phase, self.close_code, self.error = "draining", code, error
        if error is not None:
            self.runtime.record_error(error)
        self._close_task = asyncio.create_task(
            self._close(), context=Context(), name="ws-close:" + self.id
        )
        return self._close_task

    async def close(self, code=1001):
        await asyncio.shield(self.request_close(code))

    async def _close(self):
        try:
            if self.reader is not None:
                self.reader.cancel()
                await asyncio.gather(self.reader, return_exceptions=True)
            if self.close_code == 1001:
                try:
                    async with asyncio.timeout(self.runtime.settings.shutdown_seconds):
                        await self.inbound.join()
                        await self.outbound.join()
                except TimeoutError:
                    pass
            self.phase = "closing"
            tasks = [*self.processors, *(() if self.sender is None else (self.sender,))]
            for task in tasks:
                task.cancel()
            if (
                self.websocket.client_state is not WebSocketState.DISCONNECTED
                and self.websocket.application_state is not WebSocketState.DISCONNECTED
            ):
                try:
                    async with asyncio.timeout(self.runtime.settings.send_timeout_seconds):
                        await self.websocket.close(self.close_code)
                except (OSError, WebSocketDisconnect, RuntimeError, TimeoutError) as error:
                    self.runtime.record_error(error)
            await asyncio.gather(*tasks, return_exceptions=True)
            for queue in (self.inbound, self.outbound):
                while not queue.empty():
                    queue.get_nowait()
                    queue.task_done()
            await self.runtime.remove(self)
        finally:
            self.phase = "closed"
            self.closed.set()
