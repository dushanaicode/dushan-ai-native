import inspect

from loguru import logger
from pydantic import ValidationError

from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.exception.websocket_exception import WebSocketException


class SocketRegistry:
    """只登记已选择的代码声明，重复与缺失策略在监听端点前拒绝。"""

    def __init__(self, components, security):
        logger.info("【WebSocketStarter 】开始登记消息处理器并校验访问策略")
        self.audiences = {}
        self.handlers = {}
        self.events = {}
        for component in components:
            for attribute, mapping in (
                ("__socket_audience__", self.audiences),
                ("__socket_handler__", self.handlers),
                ("__socket_event__", self.events),
            ):
                if attribute not in vars(component):
                    continue
                declaration = vars(component)[attribute]
                key = (
                    declaration.key
                    if attribute == "__socket_audience__"
                    else (declaration.audience, declaration.type)
                )
                if key in mapping:
                    raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)
                mapping[key] = component if attribute == "__socket_handler__" else declaration
        if not self.audiences:
            raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)
        for definition in self.audiences.values():
            security.validate_policy(definition.policy)
            security.validate_policy(definition.send_policy)
            if definition.allow_global_targets and not definition.workload_capability:
                raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)
        for (audience, _), value in (*self.handlers.items(), *self.events.items()):
            if audience not in self.audiences:
                raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)
            definition = value.__socket_handler__ if isinstance(value, type) else value
            security.validate_policy(definition.policy)
        for definition in self.events.values():
            if definition.projector is not None and (
                definition.projector not in components
                or not inspect.iscoroutinefunction(definition.projector.project)
            ):
                raise WebSocketException(WebSocketErrorCodes.CONFIGURATION)

        logger.info(
            "【WebSocketStarter 】声明与策略校验完成：受众 {} 个，处理器 {} 个，事件 {} 个",
            len(self.audiences),
            len(self.handlers),
            len(self.events),
        )

    def audience(self, key):
        if key not in self.audiences:
            raise WebSocketException(WebSocketErrorCodes.POLICY)
        return self.audiences[key]

    def event(self, audience, kind):
        try:
            return self.events[(audience, kind)]
        except KeyError as error:
            raise WebSocketException(WebSocketErrorCodes.UNKNOWN_TYPE, cause=error) from error

    def event_payload(self, audience, kind, value):
        try:
            return self.event(audience, kind).payload.model_validate(
                value, strict=True, extra="forbid"
            )
        except ValidationError as error:
            raise WebSocketException(WebSocketErrorCodes.PROTOCOL, cause=error) from error

    def policies(self, audience):
        return {
            kind: definition.policy
            for (owner, kind), definition in self.events.items()
            if owner == audience
        }
