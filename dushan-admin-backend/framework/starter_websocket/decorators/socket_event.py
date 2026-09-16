import re

from framework.starter_di.decorators.components import framework


def socket_event(definition):
    if len(definition.type) > 128:
        raise ValueError("WebSocket 事件类型过长")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", definition.type) or definition.type in {
        "ping",
        "pong",
        "error",
        "connect",
    }:
        raise ValueError("WebSocket 下行事件类型无效或占用内置类型")
    if not definition.policy.requires_identity:
        raise ValueError("WebSocket 下行事件必须声明接收权限")

    def mark(component):
        if "__socket_event__" in vars(component):
            raise ValueError("重复 WebSocket event 声明")
        component.__socket_event__ = definition
        return framework(component)

    return mark
