import time

from pydantic import Field

from framework.starter_websocket.model.client_message import ClientMessage


class SocketMessage(ClientMessage):
    """服务端信封使用毫秒时间戳，始终以 camelCase 输出。"""

    timestamp: int = Field(
        default_factory=lambda: time.time_ns() // 1_000_000, ge=0, le=9007199254740991
    )
