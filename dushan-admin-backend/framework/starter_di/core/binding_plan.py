import inspect
from collections.abc import Iterable, Mapping
from graphlib import CycleError, TopologicalSorter

from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_config.provider.config_snapshot import ConfigSnapshot
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.binding_contract import BindingContract
from framework.starter_di.core.component_binding import ComponentBinding
from framework.starter_di.core.dependency_plan import DependencyPlan
from framework.starter_di.core.lifecycle_hooks import LifecycleHooks
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_di.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class BindingPlan:
    """在创建实例之前完成条件选择、显式绑定验证和活动依赖拓扑排序。"""

    def __init__(
        self,
        components: Iterable[type],
        configuration: ConfigProvider,
        settings: DiSettings,
        enabled_modules: frozenset[str],
        instances: Mapping[type, object],
    ) -> None:
        snapshot = configuration.snapshot()
        self.configuration_revision = snapshot.revision
        candidates: dict[type, list[tuple[ComponentBinding, tuple]]] = {}
        for component in sorted(set(components), key=self.qualified_name):
            namespace = vars(component)
            if DiComponentMetadata.ATTRIBUTE not in namespace:
                continue
            metadata = namespace[DiComponentMetadata.ATTRIBUTE]
            if not isinstance(metadata, DiComponentMetadata):
                self._invalid(component, "DI 元数据类型不正确")
            if set(metadata.depends_on) - enabled_modules:
                continue
            key = component if metadata.interface is None else metadata.interface
            scope = settings.default_scope if metadata.scope is None else metadata.scope
            conditions = namespace.get(DiComponentMetadata.CONDITIONS, ())
            if not isinstance(conditions, tuple) or any(
                not callable(value) for value in conditions
            ):
                self._invalid(component, "条件声明必须是函数元组")
            binding = ComponentBinding(key, component, metadata, scope)
            candidates.setdefault(key, []).append((binding, conditions))
        self.bindings: dict[type, ComponentBinding] = {}
        for key, group in candidates.items():
            defaults = [binding for binding, conditions in group if not conditions]
            if len(defaults) > 1:
                self._conflict(key, defaults)
            active = []
            for binding, conditions in group:
                if conditions and self._matches(binding.implementation, conditions, snapshot):
                    active.append(binding)
            if len(active) > 1:
                self._conflict(key, active)
            selected = active if active else defaults
            if selected:
                self.bindings[key] = selected[0]
        reserved = set(instances) | set(configuration.model_classes)
        collision = set(self.bindings) & reserved
        if collision:
            raise DiException(
                error_code=DiErrorCodes.DUPLICATE_BINDING,
                msg="组件不能覆盖应用提供的配置或基础实例："
                + ", ".join(sorted(self.qualified_name(key) for key in collision)),
            )
        self.providers: dict[object, tuple[ComponentBinding, ...]] = {}
        self.dependencies: dict[type, DependencyPlan] = {}
        self.hooks: dict[type, dict[LifecyclePhaseEnum, tuple[str, ...]]] = {}
        provider_lists: dict[object, list[ComponentBinding]] = {}
        for binding in self.bindings.values():
            component = binding.implementation
            BindingContract.validate_implementation(binding.key, component)
            if inspect.isabstract(component):
                self._invalid(component, "不能装配抽象组件")
            self.dependencies[component] = DependencyPlan.build(component)
            hooks = {
                phase: LifecycleHooks.collect(component, phase) for phase in LifecyclePhaseEnum
            }
            self.hooks[component] = hooks
            if binding.scope is ComponentScopeEnum.TRANSIENT and (
                hooks[LifecyclePhaseEnum.DESTROY]
                or any(
                    inspect.iscoroutinefunction(getattr(component, name))
                    for name in hooks[LifecyclePhaseEnum.INITIALIZE]
                )
            ):
                raise DiException(
                    error_code=DiErrorCodes.INVALID_LIFECYCLE,
                    msg=f"瞬态组件没有异步/销毁资源的托管边界：{self.qualified_name(component)}",
                )
            for interface in binding.metadata.providers:
                if interface not in component.__mro__:
                    raise DiException(
                        error_code=DiErrorCodes.INVALID_PROVIDER,
                        msg=f"{self.qualified_name(component)} 未实现 providers 接口 {self.qualified_name(interface)}",
                    )
                provider_lists.setdefault(list[interface], []).append(binding)
        self.providers = {key: tuple(values) for key, values in provider_lists.items()}
        graph = {}
        for binding in self.bindings.values():
            dependencies = set()
            for dependency in self.dependencies[binding.implementation].dependencies:
                if dependency in reserved:
                    continue
                if dependency in self.bindings:
                    dependencies.add(self.bindings[dependency].implementation)
                elif dependency in self.providers:
                    dependencies.update(item.implementation for item in self.providers[dependency])
                else:
                    raise DiException(
                        error_code=DiErrorCodes.MISSING_BINDING,
                        msg=f"缺少依赖绑定：{self.qualified_name(binding.implementation)} -> {dependency}",
                    )
            graph[binding.implementation] = sorted(dependencies, key=self.qualified_name)
        try:
            self.order = tuple(TopologicalSorter(graph).static_order())
        except CycleError as error:
            names = " -> ".join(self.qualified_name(node) for node in error.args[1])
            raise DiException(
                error_code=DiErrorCodes.CIRCULAR_DEPENDENCY,
                msg=f"活动依赖存在循环：{names}",
                cause=error,
            ) from error
        self.by_implementation = {
            binding.implementation: binding for binding in self.bindings.values()
        }

    @staticmethod
    def _matches(component: type, conditions: tuple, configuration: ConfigSnapshot) -> bool:
        for condition in conditions:
            try:
                value = condition(configuration)
                if type(value) is not bool:
                    if inspect.iscoroutine(value):
                        value.close()
                    raise TypeError("条件函数必须返回 bool")
            except Exception as error:
                raise DiException(
                    error_code=DiErrorCodes.INVALID_DEFINITION,
                    msg=f"组件条件求值失败：{BindingPlan.qualified_name(component)}",
                    cause=error,
                ) from error
            if not value:
                return False
        return True

    @staticmethod
    def qualified_name(component: type) -> str:
        return f"{component.__module__}.{component.__qualname__}"

    @staticmethod
    def _invalid(component: type, reason: str) -> None:
        raise DiException(
            error_code=DiErrorCodes.INVALID_DEFINITION,
            msg=f"{BindingPlan.qualified_name(component)}：{reason}",
        )

    @staticmethod
    def _conflict(key: type, bindings: list[ComponentBinding]) -> None:
        raise DiException(
            error_code=DiErrorCodes.DUPLICATE_BINDING,
            msg=f"接口 {BindingPlan.qualified_name(key)} 存在多个候选："
            + ", ".join(BindingPlan.qualified_name(item.implementation) for item in bindings),
        )
