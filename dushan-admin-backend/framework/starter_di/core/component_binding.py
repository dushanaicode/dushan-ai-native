from dataclasses import dataclass

from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum


@dataclass(frozen=True, slots=True)
class ComponentBinding:
    """条件选择后唯一生效的接口与实现绑定。"""

    key: type
    implementation: type
    metadata: DiComponentMetadata
    scope: ComponentScopeEnum
