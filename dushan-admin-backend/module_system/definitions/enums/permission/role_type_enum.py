from framework.common.enums import BaseEnum


class RoleTypeEnum(BaseEnum):
    SYSTEM = (1, "内置角色")
    CUSTOM = (2, "自定义角色")
