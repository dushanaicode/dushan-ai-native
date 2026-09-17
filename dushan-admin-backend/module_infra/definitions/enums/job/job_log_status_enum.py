from framework.common.enums.base_enum import BaseEnum


class JobLogStatusEnum(BaseEnum):
    """任务日志的状态枚举"""

    RUNNING = (0, "运行中")
    SUCCESS = (1, "成功")
    FAILURE = (2, "失败")
