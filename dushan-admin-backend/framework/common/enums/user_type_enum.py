from framework.common.enums.base_enum import BaseEnum


class UserTypeEnum(BaseEnum):
    """账号类型，角色和权限另行管理。"""

    MEMBER = (1, "会员")
    ADMIN = (2, "管理员")
    CLIENT = (3, "客户端")
