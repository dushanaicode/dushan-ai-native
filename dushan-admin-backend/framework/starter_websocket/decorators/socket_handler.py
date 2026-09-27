import inspect
import re

from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_websocket.definitions.constants.websocket_constants import WebSocketConstants
from framework.starter_websocket.handler.socket_handler import SocketHandler


def socket_handler(definition):
    if len(definition.type) > 128:
        raise ValueError("WebSocket 处理器类型过长")
    if (
        not re.fullmatch(WebSocketConstants.TYPE_PATTERN, definition.type)
        or definition.type in WebSocketConstants.BUILTIN_TYPES
    ):
        raise ValueError("WebSocket 处理器类型无效或占用内置类型")
    if not definition.policy.requires_identity:
        raise ValueError("WebSocket 处理器必须显式声明受保护策略")

    def mark(component):
        if not issubclass(component, SocketHandler) or not inspect.iscoroutinefunction(
            component.handle
        ):
            raise TypeError("WebSocket 处理器必须实现异步 SocketHandler")
        if "__socket_handler__" in vars(component):
            raise ValueError("重复 WebSocket handler 声明")
        component.__socket_handler__ = definition
        return framework(scope=ComponentScopeEnum.TRANSIENT)(component)

    return mark
