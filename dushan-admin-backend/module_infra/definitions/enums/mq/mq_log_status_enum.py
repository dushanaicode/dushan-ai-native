from framework.common.enums.base_enum import BaseEnum


class MqLogStatusEnum(BaseEnum):
    """MQ 消费日志的状态枚举"""

    CONSUMING = (0, "消费中")
    SUCCESS = (1, "消费成功")
    FAILURE = (2, "消费失败")
