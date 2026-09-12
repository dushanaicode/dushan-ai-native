from collections.abc import Callable
from typing import TypeVar

from framework.starter_config.provider.config_snapshot import ConfigSnapshot
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata

T = TypeVar("T", bound=type)


def conditional(predicate: Callable[[ConfigSnapshot], bool]) -> Callable[[T], T]:
    """按当前应用配置选择候选；条件在容器启动时求值，不访问全局配置。"""
    if not callable(predicate):
        raise TypeError("条件必须是接收 ConfigSnapshot 的函数")

    def mark(cls: T) -> T:
        conditions = vars(cls).get(DiComponentMetadata.CONDITIONS, ())
        setattr(cls, DiComponentMetadata.CONDITIONS, (*conditions, predicate))
        return cls

    return mark
