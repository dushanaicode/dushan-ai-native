from dataclasses import dataclass
from typing import ClassVar

from framework.common.enums.base_enum import BaseEnum
from framework.common.importing.package_locator import PackageLocator
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum


@dataclass(frozen=True, slots=True)
class DiComponentMetadata:
    """DI 专用静态契约，与共享扫描标记分离；None scope 交给 YAML 决定。"""

    ATTRIBUTE: ClassVar[str] = "__di_metadata__"
    CONDITIONS: ClassVar[str] = "__di_conditions__"
    role: BaseEnum
    interface: type | None
    scope: ComponentScopeEnum | None
    providers: tuple[type, ...]
    depends_on: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.role, BaseEnum) or not isinstance(self.role.value, str):
            raise TypeError("DI 角色必须是字符串编码的 BaseEnum 成员")
        if self.interface is not None and not isinstance(self.interface, type):
            raise TypeError("DI interface 必须是类型")
        if self.scope is not None and not isinstance(self.scope, ComponentScopeEnum):
            raise TypeError("DI scope 必须是 ComponentScopeEnum")
        if any(not isinstance(value, type) for value in self.providers) or len(
            set(self.providers)
        ) != len(self.providers):
            raise TypeError("providers 必须是无重复的类型列表")
        if any(not PackageLocator.is_valid_name(value) for value in self.depends_on) or len(
            set(self.depends_on)
        ) != len(self.depends_on):
            raise ValueError("depends_on 必须是无重复的模块 ID")
