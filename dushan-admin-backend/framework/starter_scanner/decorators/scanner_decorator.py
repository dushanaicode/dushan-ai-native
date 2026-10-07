from collections.abc import Callable
from typing import TypeVar

from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.component_type_enum import ComponentTypeEnum

T = TypeVar("T", bound=type)


def scanner(_cls: T | None = None) -> T | Callable[[T], T]:
    """标记通用类定义，支持 @scanner 和 @scanner()，不创建实例或注册全局状态。"""

    def mark(cls: T) -> T:
        ComponentMetadata(ComponentTypeEnum.COMPONENT).attach(cls)
        return cls

    return mark if _cls is None else mark(_cls)
