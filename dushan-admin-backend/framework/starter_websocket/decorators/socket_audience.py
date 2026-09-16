import re

from framework.starter_di.decorators.components import framework


def socket_audience(definition):
    """注册模块自己的投递域，不在框架中写死业务枚举。"""
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", definition.key):
        raise ValueError("WebSocket audience 无效")
    if not definition.policy.requires_identity or not definition.send_policy.requires_identity:
        raise ValueError("WebSocket audience 必须声明接入和发送权限")

    def mark(component):
        if "__socket_audience__" in vars(component):
            raise ValueError("重复 WebSocket audience 声明")
        component.__socket_audience__ = definition
        return framework(component)

    return mark
