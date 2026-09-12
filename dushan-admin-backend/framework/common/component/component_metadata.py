from dataclasses import dataclass
from typing import ClassVar

from framework.common.enums.component_type_enum import ComponentTypeEnum


@dataclass(frozen=True, slots=True)
class ComponentMetadata:
    """类定义的静态标记；应用归属由模块声明决定，不存放运行对象。"""

    ATTRIBUTE: ClassVar[str] = "__component_metadata__"
    component_type: ComponentTypeEnum

    def __post_init__(self) -> None:
        """拒绝未声明的类别，避免自由字典形成第二套接口。"""
        if not isinstance(self.component_type, ComponentTypeEnum):
            raise TypeError("组件类别必须是 ComponentTypeEnum")

    def attach(self, target: type) -> None:
        """只标记类本身；重复装饰明确失败，继承不会自动重复声明。"""
        if not isinstance(target, type):
            raise TypeError("组件装饰器只能标记类")
        if self.ATTRIBUTE in vars(target):
            raise ValueError(f"组件重复标记: {target.__module__}.{target.__qualname__}")
        setattr(target, self.ATTRIBUTE, self)
