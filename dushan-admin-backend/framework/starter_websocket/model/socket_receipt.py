from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class SocketReceipt:
    """入队/Redis 接收数量，不代表客户端收到或处理。"""

    transport: Literal["local", "redis"]
    accepted: int
