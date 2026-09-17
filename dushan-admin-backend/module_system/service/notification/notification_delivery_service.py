from typing import Any, Protocol, runtime_checkable

from module_system.framework.notification.delivery.delivery_attempt import DeliveryAttempt


@runtime_checkable
class NotificationDeliveryService(Protocol):
    async def claim(self, kind: str, identifier: int) -> DeliveryAttempt | None: ...
    async def started(self, kind: str, identifier: int, attempt: DeliveryAttempt) -> None: ...
    async def finish(
        self, kind: str, identifier: int, attempt: DeliveryAttempt, **values: Any
    ) -> None: ...
