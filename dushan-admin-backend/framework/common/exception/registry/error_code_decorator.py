from collections.abc import Callable
from typing import TypeVar

from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.component_type_enum import ComponentTypeEnum

T = TypeVar("T", bound=type)


def error_code(_cls: T | None = None) -> T | Callable[[T], T]:
    """标记错误码常量类，供扫描器发现。

    仅写公共不可变元数据，不导入扫描器、不注册运行对象。
    """

    def wrapper(cls: T) -> T:
        """为错误码常量类写入组件扫描元数据。"""
        ComponentMetadata(ComponentTypeEnum.ERROR_CODE).attach(cls)
        return cls

    if _cls is None:
        return wrapper
    return wrapper(_cls)
