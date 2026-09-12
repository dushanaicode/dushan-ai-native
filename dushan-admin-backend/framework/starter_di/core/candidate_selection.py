import inspect
from collections.abc import Iterable
from typing import NoReturn, get_args, get_origin

from framework.starter_config.provider.config_snapshot import ConfigSnapshot
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.binding_diagnostic import BindingDiagnostic
from framework.starter_di.core.component_binding import ComponentBinding
from framework.starter_di.decorators.di_component_metadata import DiComponentMetadata
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class CandidateSelection:
    """在同一配置快照上收集 DI 候选并完成条件选择，记录每个候选的结果与原因。

    构造只保存输入；select 对每个候选的条件函数只求值一次，之后的诊断查询
    不再重新求值。冲突只记录不抛出，由 BindingPlan 在验证阶段统一失败，
    因此即使启动失败，已记录的候选解释仍可查询。
    """

    def __init__(
        self, snapshot: ConfigSnapshot, settings: DiSettings, enabled_modules: frozenset[str]
    ) -> None:
        self.configuration_revision = snapshot.revision
        self._snapshot = snapshot
        self._settings = settings
        self._enabled_modules = enabled_modules
        self.bindings: dict[type, ComponentBinding] = {}
        self.conflicts: dict[type, tuple[ComponentBinding, ...]] = {}
        self._diagnostics: list[BindingDiagnostic] = []

    @property
    def diagnostics(self) -> tuple[BindingDiagnostic, ...]:
        return tuple(self._diagnostics)

    def select(self, components: Iterable[type]) -> None:
        """按稳定顺序收集带元数据的候选，再按绑定键完成一次性选择。"""
        candidates: dict[type, list[tuple[ComponentBinding, tuple]]] = {}
        for component in sorted(set(components), key=self.qualified_name):
            candidate = self._candidate(component)
            if candidate is not None:
                candidates.setdefault(candidate[0].key, []).append(candidate)
        for key, group in candidates.items():
            self._select_group(key, group)

    def explain(self, key: object) -> str:
        """说明某个绑定键为何没有生效候选，供缺少绑定的错误信息使用。"""
        interface = get_args(key)[0] if get_origin(key) is list else key
        name = self.qualified_name(interface) if isinstance(interface, type) else str(interface)
        related = [
            item
            for item in self._diagnostics
            if item.outcome is not BindingOutcomeEnum.SELECTED
            and (name in item.providers if get_origin(key) is list else item.key == name)
        ]
        if not related:
            return "没有任何候选声明该绑定键"
        return "；".join(
            f"{item.component} {item.outcome.label}（{item.reason}）" for item in related
        )

    def _candidate(self, component: type) -> tuple[ComponentBinding, tuple] | None:
        namespace = vars(component)
        if DiComponentMetadata.ATTRIBUTE not in namespace:
            return None
        metadata = namespace[DiComponentMetadata.ATTRIBUTE]
        if not isinstance(metadata, DiComponentMetadata):
            self._invalid(component, "DI 元数据类型不正确")
        key = component if metadata.interface is None else metadata.interface
        scope = self._settings.default_scope if metadata.scope is None else metadata.scope
        binding = ComponentBinding(key, component, metadata, scope)
        missing = sorted(set(metadata.depends_on) - self._enabled_modules)
        if missing:
            self._record(
                binding, BindingOutcomeEnum.MISSING_MODULE, "未启用模块 " + ", ".join(missing)
            )
            return None
        conditions = namespace.get(DiComponentMetadata.CONDITIONS, ())
        if not isinstance(conditions, tuple) or any(not callable(value) for value in conditions):
            self._invalid(component, "条件声明必须是函数元组")
        return binding, conditions

    def _select_group(self, key: type, group: list[tuple[ComponentBinding, tuple]]) -> None:
        """多个默认候选直接冲突且不再求值条件；多个条件成立的候选同样冲突。"""
        defaults = [binding for binding, conditions in group if not conditions]
        if len(defaults) > 1:
            self._conflict(key, defaults)
            return
        active = [
            binding
            for binding, conditions in group
            if conditions and self._matches(binding.implementation, conditions)
        ]
        if len(active) > 1:
            self._conflict(key, active)
        chosen = active if active else defaults
        if chosen and key not in self.conflicts:
            self.bindings[key] = chosen[0]
            self._record(
                chosen[0], BindingOutcomeEnum.SELECTED, "条件成立" if active else "默认实现"
            )
        for binding, conditions in group:
            if binding in chosen:
                continue
            if conditions:
                self._record(binding, BindingOutcomeEnum.CONDITION_FALSE, "条件函数返回 False")
            else:
                self._record(
                    binding,
                    BindingOutcomeEnum.DEFAULT_REPLACED,
                    "被条件候选替代：" + ", ".join(self._names(active)),
                )

    def _matches(self, component: type, conditions: tuple) -> bool:
        for condition in conditions:
            try:
                value = condition(self._snapshot)
                if type(value) is not bool:
                    if inspect.iscoroutine(value):
                        value.close()
                    raise TypeError("条件函数必须返回 bool")
            except Exception as error:
                raise DiException(
                    error_code=DiErrorCodes.INVALID_DEFINITION,
                    msg=f"组件条件求值失败：{self.qualified_name(component)}",
                    cause=error,
                ) from error
            if not value:
                return False
        return True

    def _conflict(self, key: type, bindings: list[ComponentBinding]) -> None:
        self.conflicts[key] = tuple(bindings)
        for binding in bindings:
            others = [item for item in bindings if item is not binding]
            self._record(
                binding,
                BindingOutcomeEnum.CONFLICT,
                "同时存在候选：" + ", ".join(self._names(others)),
            )

    def _record(self, binding: ComponentBinding, outcome: BindingOutcomeEnum, reason: str) -> None:
        self._diagnostics.append(
            BindingDiagnostic(
                self.qualified_name(binding.implementation),
                self.qualified_name(binding.key),
                tuple(self.qualified_name(item) for item in binding.metadata.providers),
                outcome,
                reason,
            )
        )

    @classmethod
    def _names(cls, bindings: list[ComponentBinding]) -> list[str]:
        return [cls.qualified_name(binding.implementation) for binding in bindings]

    @staticmethod
    def qualified_name(component: type) -> str:
        return f"{component.__module__}.{component.__qualname__}"

    @staticmethod
    def describe_key(key: object) -> str:
        """把绑定键格式化为可读名称，list[接口] 保留列表形式。"""
        if get_origin(key) is list and get_args(key):
            return f"list[{CandidateSelection.describe_key(get_args(key)[0])}]"
        if isinstance(key, type):
            return CandidateSelection.qualified_name(key)
        return str(key)

    @staticmethod
    def _invalid(component: type, reason: str) -> NoReturn:
        raise DiException(
            error_code=DiErrorCodes.INVALID_DEFINITION,
            msg=f"{CandidateSelection.qualified_name(component)}：{reason}",
        )
