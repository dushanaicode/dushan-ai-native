from typing import TypeVar

from framework.starter_di.context.application_context import ApplicationContext

T = TypeVar("T")


def get_bean(bean_type: type[T]) -> T:
    """外部调用者的薄框架入口；应用选择和解析只由正式上下文负责。"""
    return ApplicationContext.current().get_bean(bean_type)
