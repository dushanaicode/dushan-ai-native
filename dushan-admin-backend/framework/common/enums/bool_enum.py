from framework.common.enums.base_enum import BaseEnum


class BoolEnum(BaseEnum):
    """业务字段的是/否编码，使用整数 0 和 1。"""

    NO = (0, "否")
    YES = (1, "是")
