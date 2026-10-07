from collections.abc import Awaitable, Callable
from typing import Literal, Protocol, runtime_checkable

from module_system.framework.notification.delivery.delivery_attempt import (
    DeliveryRequestStartedCallback,
)


@runtime_checkable
class NotificationDeliveryService(Protocol):
    async def execute[Result](
        self,
        kind: Literal["mail", "sms"],
        identifier: int,
        *,
        send: Callable[[DeliveryRequestStartedCallback], Awaitable[Result]],
        result_values: Callable[[Result], dict[str, int | str | None]],
    ) -> None:
        """认领并执行一次外发，统一保存渠道结果及明确失败、取消和未知状态。"""
        ...
