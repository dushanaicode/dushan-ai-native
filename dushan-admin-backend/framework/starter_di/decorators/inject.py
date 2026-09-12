from typing import Any

from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class Inject:
    """按实例所属容器解析带类型注解的字段，不使用全局容器。

    每次读取都遵循容器 scope；手工构造对象可先赋值用于独立测试，
    进入容器后字段不能覆盖。字段注入要求实例支持 __dict__。
    """

    def __init__(self) -> None:
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        if self.name is not None:
            raise TypeError("同一 Inject 描述符不能绑定多个字段")
        self.name = name

    def __get__(self, instance: Any, owner: type):
        if instance is None:
            return self
        namespace = vars(instance)
        if "__di_resolver__" in namespace:
            return namespace["__di_resolver__"](namespace["__di_fields__"][self.name])
        if self.name in namespace:
            return namespace[self.name]
        raise DiException(
            error_code=DiErrorCodes.MISSING_BINDING,
            msg=f"字段尚未注入：{owner.__module__}.{owner.__qualname__}.{self.name}",
        )

    def __set__(self, instance: Any, value: Any) -> None:
        if "__di_resolver__" in vars(instance):
            raise DiException(
                error_code=DiErrorCodes.INVALID_DEFINITION,
                msg=f"容器管理的 Inject 字段不能覆盖：{self.name}",
            )
        vars(instance)[self.name] = value
