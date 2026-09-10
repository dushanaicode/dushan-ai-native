from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T", bound=type)


def error_code(_cls: T | None = None) -> T | Callable[[T], T]:
    """标记错误码常量类，供扫描器发现。

    独立于 starter_di 实现，避免与 di_error_code_constants 形成循环导入。
    写入与扫描器兼容的 __component_metadata__。
    """

    def wrapper(cls: T) -> T:
        """为错误码常量类写入组件扫描元数据。"""
        cls.__component_metadata__ = {
            "component_type": "error_code",
            "name": cls.__name__,
            "module": cls.__module__.split(".")[0],
            "details": {"component_type": "error_code", "system": "exception"},
            "di_managed": True,
        }
        return cls

    if _cls is None:
        return wrapper
    return wrapper(_cls)


__all__ = ["error_code"]
