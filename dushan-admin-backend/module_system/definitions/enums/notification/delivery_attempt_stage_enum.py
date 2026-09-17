from framework.common.enums.base_enum import BaseEnum


class DeliveryAttemptStageEnum(BaseEnum):
    """外部通知的一次发送尝试所处阶段。"""

    CLAIMED = ("claimed", "已领取，尚未进入外部请求边界")
    REQUEST_STARTED = ("request_started", "外部请求已进入不确定结果边界")
