from framework.common.enums.base_enum import BaseEnum


class SocketTargetKind(BaseEnum):
    """发送目标的定位方式。"""

    CLIENT = ("client", "指定连接")
    MEMBER = ("member", "指定成员")
    TENANT = ("tenant", "指定租户")
    AUDIENCE = ("audience", "订阅分组")
