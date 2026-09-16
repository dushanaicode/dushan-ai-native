import inspect
import re

from pydantic import BaseModel

from framework.starter_di.decorators.components import framework
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_mq.handler.message_handler import MessageHandler
from framework.starter_mq.model.consumer_definition import ConsumerDefinition


def consumer(definition: ConsumerDefinition):
    """显式类型注册，不按外部字符串导入类或依赖类名作为稳定标识。"""
    if not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", definition.key):
        raise ValueError("消费者 key 无效")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}", definition.destination):
        raise ValueError("消息目的地无效")
    if not isinstance(definition.message, type) or not issubclass(definition.message, BaseModel):
        raise TypeError("消费者必须声明 Pydantic 消息模型")

    def mark(handler):
        if not issubclass(handler, MessageHandler) or not inspect.iscoroutinefunction(
            handler.handle
        ):
            raise TypeError("消费者必须实现异步 MessageHandler")
        if "__mq_consumer__" in vars(handler):
            raise ValueError("消费者不允许重复声明")
        handler.__mq_consumer__ = definition
        return framework(scope=ComponentScopeEnum.TRANSIENT)(handler)

    return mark
