from framework.common.enums.base_enum import BaseEnum


class StatusEnum(BaseEnum):
    """业务字段的开启和关闭状态，1 表示开启，0 表示关闭。"""

    DISABLE = (0, "关闭")
    ENABLE = (1, "开启")
