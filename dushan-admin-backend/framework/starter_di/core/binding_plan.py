import inspect
from collections.abc import Mapping
from graphlib import CycleError, TopologicalSorter

from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.core.binding_contract import BindingContract
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.core.component_binding import ComponentBinding
from framework.starter_di.core.dependency_plan import DependencyPlan
from framework.starter_di.core.lifecycle_hooks import LifecycleHooks
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_di.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class BindingPlan:
    """在创建实例之前完成显式绑定验证和活动依赖拓扑排序。

    候选收集与条件选择由 CandidateSelection 先行完成；本类只消费其结果：
    先让已记录的冲突失败，再验证契约、依赖声明与生命周期，最后排序。
    """

    def __init__(
        self,
        selection: CandidateSelection,
        configuration: ConfigProvider,
        instances: Mapping[type, object],
    ) -> None:
        self.selection = selection
        self.configuration_revision = selection.configuration_revision
        self.bindings: dict[type, ComponentBinding] = dict(selection.bindings)
        for key, bindings in selection.conflicts.items():
            self._conflict(key, bindings)
        reserved = set(instances) | set(configuration.model_classes)
        collision = set(self.bindings) & reserved
        if collision:
            raise DiException(
                error_code=DiErrorCodes.DUPLICATE_BINDING,
                msg="组件不能覆盖应用提供的配置或基础实例："
                + ", ".join(sorted(self.qualified_name(key) for key in collision)),
            )
        self.dependencies: dict[type, DependencyPlan] = {}
        self.hooks: dict[type, dict[LifecyclePhaseEnum, tuple[str, ...]]] = {}
        self.providers: dict[object, tuple[ComponentBinding, ...]] = self._validate_bindings()
        self.order: tuple[type, ...] = self._order(reserved)
        self.by_implementation = {
            binding.implementation: binding for binding in self.bindings.values()
        }

    def _validate_bindings(self) -> dict[object, tuple[ComponentBinding, ...]]:
        """逐个验证实现契约、依赖声明、生命周期边界与 providers 接口。"""
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
        return {key: tuple(values) for key, values in provider_lists.items()}

    def _order(self, reserved: set[object]) -> tuple[type, ...]:
        """缺少绑定时给出已知候选的落选原因；活动依赖成环时列出环路。"""
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
                        msg=(
                            f"缺少依赖绑定：{self.qualified_name(binding.implementation)} -> "
                            f"{CandidateSelection.describe_key(dependency)}；"
                            f"{self.selection.explain(dependency)}"
                        ),
                    )
            graph[binding.implementation] = sorted(dependencies, key=self.qualified_name)
        try:
            return tuple(TopologicalSorter(graph).static_order())
        except CycleError as error:
            names = " -> ".join(self.qualified_name(node) for node in error.args[1])
            raise DiException(
                error_code=DiErrorCodes.CIRCULAR_DEPENDENCY,
                msg=f"活动依赖存在循环：{names}",
                cause=error,
            ) from error

    @staticmethod
    def qualified_name(component: type) -> str:
        return CandidateSelection.qualified_name(component)

    @staticmethod
    def _invalid(component: type, reason: str) -> None:
        raise DiException(
            error_code=DiErrorCodes.INVALID_DEFINITION,
            msg=f"{BindingPlan.qualified_name(component)}：{reason}",
        )

    @staticmethod
    def _conflict(key: type, bindings: tuple[ComponentBinding, ...]) -> None:
        raise DiException(
            error_code=DiErrorCodes.DUPLICATE_BINDING,
            msg=f"接口 {BindingPlan.qualified_name(key)} 存在多个候选："
            + ", ".join(BindingPlan.qualified_name(item.implementation) for item in bindings),
        )
