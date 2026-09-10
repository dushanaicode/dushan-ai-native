from framework.common.enums.base_enum import BaseEnum


class BuiltinTypeEnum(BaseEnum):
    """区分内置数据和用户自定义数据。"""

    BUILTIN = (1, "内置")
    CUSTOM = (2, "自定义")
