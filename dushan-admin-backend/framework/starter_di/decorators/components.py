from collections.abc import Callable, Sequence
from typing import TypeVar

from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.base_enum import BaseEnum
from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_di.enums.component_role_enum import ComponentRoleEnum
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum

T = TypeVar("T", bound=type)


def component(role: BaseEnum) -> Callable:
    """同一套 DI 标记规则供不同角色复用，不生成任何运行实例。"""

    def decorate(
        _cls: T | None = None,
        *,
        interface: type | None = None,
        scope: ComponentScopeEnum | None = None,
        providers: Sequence[type] = (),
        depends_on: Sequence[str] = (),
    ) -> T | Callable[[T], T]:
        if isinstance(providers, (str, bytes)) or isinstance(depends_on, (str, bytes)):
            raise TypeError("providers 和 depends_on 必须是列表或元组，不能是字符串")
        metadata = DiComponentMetadata(role, interface, scope, tuple(providers), tuple(depends_on))

        def mark(cls: T) -> T:
            ComponentMetadata(ComponentTypeEnum.COMPONENT).attach(cls)
            setattr(cls, DiComponentMetadata.ATTRIBUTE, metadata)
            return cls

        return mark if _cls is None else mark(_cls)

    return decorate


service = component(ComponentRoleEnum.SERVICE)
repository = component(ComponentRoleEnum.REPOSITORY)
mapper = component(ComponentRoleEnum.MAPPER)
aggregate_mapper = component(ComponentRoleEnum.AGGREGATE_MAPPER)
dao = component(ComponentRoleEnum.DAO)
framework = component(ComponentRoleEnum.FRAMEWORK)
starter = component(ComponentRoleEnum.STARTER)
util = component(ComponentRoleEnum.UTIL)
websocket = component(ComponentRoleEnum.WEBSOCKET)
redis = component(ComponentRoleEnum.REDIS)
config_builder = component(ComponentRoleEnum.CONFIG_BUILDER)
bootstrap = component(ComponentRoleEnum.BOOTSTRAP)
