import inspect

from pydantic import ValidationError

from framework.starter_websocket.exception.socket_exception import SocketException


class SocketRegistry:
    """只登记已选择的代码声明，重复与缺失策略在监听端点前拒绝。"""

    def __init__(self, components, security):
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
                    raise SocketException("configuration")
                mapping[key] = component if attribute == "__socket_handler__" else declaration
        if not self.audiences:
            raise SocketException("configuration")
        for definition in self.audiences.values():
            security.validate_policy(definition.policy)
            security.validate_policy(definition.send_policy)
            if definition.allow_global_targets and not definition.workload_capability:
                raise SocketException("configuration")
        for (audience, _), value in (*self.handlers.items(), *self.events.items()):
            if audience not in self.audiences:
                raise SocketException("configuration")
            definition = value.__socket_handler__ if isinstance(value, type) else value
            security.validate_policy(definition.policy)
        for definition in self.events.values():
            if definition.projector is not None and (
                definition.projector not in components
                or not inspect.iscoroutinefunction(definition.projector.project)
            ):
                raise SocketException("configuration")

    def audience(self, key):
        if key not in self.audiences:
            raise SocketException("policy")
        return self.audiences[key]

    def event(self, audience, kind):
        try:
            return self.events[(audience, kind)]
        except KeyError as error:
            raise SocketException("unknown_type", cause=error) from error

    def event_payload(self, audience, kind, value):
        try:
            return self.event(audience, kind).payload.model_validate(
                value, strict=True, extra="forbid"
            )
        except ValidationError as error:
            raise SocketException("protocol", cause=error) from error

    def policies(self, audience):
        return {
            kind: definition.policy
            for (owner, kind), definition in self.events.items()
            if owner == audience
        }
