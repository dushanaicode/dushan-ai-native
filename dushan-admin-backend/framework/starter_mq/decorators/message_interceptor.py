import inspect

from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum


def message_interceptor(*, order: int):
    def mark(component):
        if not inspect.isfunction(component.enter) or "__mq_interceptor__" in vars(component):
            raise TypeError("MQ 拦截器必须提供 enter 上下文管理器")
        component.__mq_interceptor__ = order
        return framework(scope=ComponentScopeEnum.TRANSIENT)(component)

    return mark
