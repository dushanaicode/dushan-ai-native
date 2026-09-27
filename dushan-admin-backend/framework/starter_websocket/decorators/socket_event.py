import re

from framework.starter_di.decorators.components import framework
from framework.starter_websocket.definitions.constants.websocket_constants import WebSocketConstants


def socket_event(definition):
    if len(definition.type) > 128:
        raise ValueError("WebSocket 事件类型过长")
    if (
        not re.fullmatch(WebSocketConstants.TYPE_PATTERN, definition.type)
        or definition.type in WebSocketConstants.BUILTIN_TYPES
    ):
        raise ValueError("WebSocket 下行事件类型无效或占用内置类型")
    if not definition.policy.requires_identity:
        raise ValueError("WebSocket 下行事件必须声明接收权限")

    def mark(component):
        if "__socket_event__" in vars(component):
            raise ValueError("重复 WebSocket event 声明")
        component.__socket_event__ = definition
        return framework(component)

    return mark
