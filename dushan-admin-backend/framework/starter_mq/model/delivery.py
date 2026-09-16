from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(slots=True)
class Delivery:
    """驱动提供的单条在途消息；每次操作只结算这一条或当前分区 offset。"""

    body: bytes
    reference: str
    retry: bool
    acknowledge: Callable[[], Awaitable[None]]
    release: Callable[[], Awaitable[None]]
