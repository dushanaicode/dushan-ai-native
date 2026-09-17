from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from module_system.definitions.enums.notification.delivery_attempt_stage_enum import (
    DeliveryAttemptStageEnum,
)

DeliveryRequestStartedCallback = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class DeliveryAttempt:
    """数据库 claim 与当前进程网络边界的关联状态。"""

    claim_token: str
    stage: DeliveryAttemptStageEnum = DeliveryAttemptStageEnum.CLAIMED
