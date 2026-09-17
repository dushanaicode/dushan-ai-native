from framework.common.enums.base_enum import BaseEnum


class JobStatusEnum(BaseEnum):
    """任务状态的枚举"""

    INIT = (0, "初始化中")
    NORMAL = (1, "开启")
    STOP = (2, "暂停")
