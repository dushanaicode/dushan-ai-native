from dataclasses import dataclass

from pydantic import BaseModel

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.exception.websocket_exception import WebSocketException
from framework.starter_websocket.model.socket_message import SocketMessage


@dataclass(slots=True, repr=False)
class SocketContext:
    """仅在当前消息执行内可用的回复端口，不向业务暴露底层连接表。"""

    _connection: object
    execution: object
    request_id: str | None
    active: bool = True

    @property
    def client_id(self):
        return self._connection.id

    @property
    def client_ip(self):
        return self._connection.client_ip

    @property
    def audience(self):
        return self._connection.audience

    async def reply(self, kind, payload):
        if (
            not self.active
            or not self.execution.active
            or ApplicationContext.current_execution() is not self.execution
        ):
            raise WebSocketException(WebSocketErrorCodes.CLOSED)
        runtime = self._connection.runtime
        value = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        checked = runtime.registry.event_payload(self.audience, kind, value)
        if kind not in self._connection.allowed_events:
            raise WebSocketException(WebSocketErrorCodes.POLICY)
        message = SocketMessage(
            type=kind, payload=checked.model_dump(mode="json"), request_id=self.request_id
        )
        if not self._connection.enqueue(message, continuation=True):
            raise WebSocketException(WebSocketErrorCodes.CAPACITY)
