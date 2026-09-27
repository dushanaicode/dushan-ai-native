from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class Delivery:
    """驱动提供的单条在途消息；每次操作只结算这一条或当前分区 offset。"""

    body: bytes
    retry: bool
    _acknowledge: Callable[[], Awaitable[None]]
    _release: Callable[[], Awaitable[None]]
    _settled: bool = field(default=False, init=False)

    async def acknowledge(self) -> None:
        await self._acknowledge()
        self._settled = True

    async def release(self) -> None:
        """关闭兜底不重复释放已经确认或释放的消息。"""
        if not self._settled:
            await self._release()
            self._settled = True
