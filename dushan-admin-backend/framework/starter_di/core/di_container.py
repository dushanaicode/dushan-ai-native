import asyncio
import inspect
from collections.abc import Iterable, Mapping
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from threading import Condition, RLock
from time import perf_counter
from typing import TYPE_CHECKING, TypeVar, cast

from injector import Injector, InstanceProvider, singleton
from loguru import logger

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.enums.base_enum import BaseEnum
from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.binding_contract import BindingContract
from framework.starter_di.core.binding_diagnostic import BindingDiagnostic
from framework.starter_di.core.binding_plan import BindingPlan
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.core.component_binding import ComponentBinding
from framework.starter_di.core.component_provider import ComponentProvider
from framework.starter_di.core.config_model_provider import ConfigModelProvider
from framework.starter_di.core.execution_frame import ExecutionFrame
from framework.starter_di.core.lifecycle_hooks import LifecycleHooks
from framework.starter_di.core.list_binding_provider import ListBindingProvider
from framework.starter_di.core.state.state_manager import StateManager
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

T = TypeVar("T")

if TYPE_CHECKING:
    from framework.starter_di.context.application_context import ApplicationContext


class DiContainer:
    """当前应用的显式 DI 容器，不使用全局单例或扫描注册表。

    构造只保存输入；startup 先验证全部活动绑定再按依赖顺序初始化单例。
    READY 后 get 可在线程间使用，配置来自已传入的 ConfigProvider。
    shutdown 关闭创建入口，等待已开始的解析，并逆序清理本容器拥有的单例。
    """

    def __init__(
        self,
        components: Iterable[type],
        *,
        configuration: ConfigProvider,
        settings: DiSettings,
        enabled_modules: frozenset[str],
        instances: Mapping[type, object] | None = None,
    ) -> None:
        self.configuration = configuration
        self.settings = settings
        self.state_manager = StateManager()
        self._components = tuple(components)
        self._enabled_modules = enabled_modules
        self._instances = {} if instances is None else dict(instances)
        core = {DiContainer: self, ConfigProvider: configuration, StateManager: self.state_manager}
        if (
            set(core) & self._instances.keys()
            or set(configuration.model_classes) & self._instances.keys()
        ):
            raise DiException(
                error_code=DiErrorCodes.DUPLICATE_BINDING,
                msg="外部实例不能覆盖容器核心或已注册配置模型",
            )
        for key, instance in self._instances.items():
            BindingContract.validate_instance(key, instance)
        self._instances.update(core)
        self._condition = Condition(RLock())
        self._state = ContainerStateEnum.NEW
        self._active_gets = 0
        self._selection: CandidateSelection | None = None
        self._plan: BindingPlan | None = None
        self._injector: Injector | None = None
        self._created: list[tuple[ComponentBinding, object]] = []
        self._ready_types: set[type] = set()
        self._lifecycle_context = ContextVar(f"di_lifecycle_{id(self)}", default=None)
        self._resolution_path = ContextVar(f"di_resolution_{id(self)}", default=())
        self._shutdown_task: asyncio.Task[None] | None = None
        self._resolution_count = 0
        self._resolution_seconds = 0.0
        self._application: ApplicationContext | None = None

    def attach_application(
        self, application: "ApplicationContext", instances: Mapping[type, object]
    ) -> None:
        """启动前一次绑定运行上下文和任务入口，不覆盖既有实例或配置模型。"""
        with self._condition:
            if self._state is not ContainerStateEnum.NEW or self._application is not None:
                raise DiException(error_code=DiErrorCodes.NOT_READY)
            if set(instances) & (self._instances.keys() | set(self.configuration.model_classes)):
                raise DiException(error_code=DiErrorCodes.DUPLICATE_BINDING)
            for key, instance in instances.items():
                BindingContract.validate_instance(key, instance)
            self._instances.update(instances)
            self._application = application

    @property
    def state(self) -> ContainerStateEnum:
        with self._condition:
            return self._state

    async def startup(self) -> None:
        """配置与所有绑定成功后才创建单例，所有初始化成功后才进入 READY。"""
        with self._condition:
            if not self.settings.enabled or self._state is not ContainerStateEnum.NEW:
                raise DiException(
                    error_code=DiErrorCodes.NOT_READY, msg="DI 已禁用或此容器已经开始过生命周期"
                )
            self._state = ContainerStateEnum.STARTING
        frame = ExecutionFrame(LifecyclePhaseEnum.INITIALIZE)
        token = self._lifecycle_context.set(frame)
        try:
            selection = CandidateSelection(
                self.configuration.snapshot(), self.settings, self._enabled_modules
            )
            self._selection = selection
            selection.select(self._components)
            self._plan = BindingPlan(selection, self.configuration, self._instances)
            self._log_selection(selection)
            injector = Injector(auto_bind=False)
            self._injector = injector
            for key, instance in self._instances.items():
                injector.binder.bind(key, to=InstanceProvider(instance))
            for model in self.configuration.model_classes:
                injector.binder.bind(model, to=ConfigModelProvider(self.configuration, model))
            for key, binding in self._plan.bindings.items():
                injector.binder.bind(
                    key,
                    to=ComponentProvider(self, binding),
                    scope=singleton if binding.scope is ComponentScopeEnum.SINGLETON else None,
                )
            for interface, bindings in self._plan.providers.items():
                for binding in bindings:
                    injector.binder.multibind(interface, to=ListBindingProvider(binding.key))
            for component in self._plan.order:
                binding = self._plan.by_implementation[component]
                if binding.scope is ComponentScopeEnum.SINGLETON:
                    instance = injector.get(binding.key)
                    for name in self._plan.hooks[component][LifecyclePhaseEnum.INITIALIZE]:
                        await self._invoke_hook(instance, name, LifecyclePhaseEnum.INITIALIZE)
                    self._ready_types.add(component)
            with self._condition:
                self._state = ContainerStateEnum.READY
        except BaseException as primary:
            with self._condition:
                self._state = ContainerStateEnum.STOPPING
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                self._close, "DI 启动失败清理"
            )
            errors = [] if error is None else [error]
            if error is not None and primary.__cause__ is not None:
                errors.insert(0, primary.__cause__)
            CleanupUtils.raise_collected_cleanup_errors(
                "DI 启动与清理失败", errors, caller_cancellation=cancellation, primary_error=primary
            )
        finally:
            frame.active = False
            self._lifecycle_context.reset(token)

    def get(self, key: type[T]) -> T:
        """解析显式类型或 list[接口]；瞬态每次解析新建，不能越过就绪/关闭边界。"""
        if self._application is not None:
            self._application.validate_resolution()
        started = perf_counter() if self.settings.metrics_enabled else None
        with self._condition:
            allowed = self._state is ContainerStateEnum.READY or (
                self._has_lifecycle_access()
                and self._state in {ContainerStateEnum.STARTING, ContainerStateEnum.STOPPING}
            )
            if not allowed:
                raise DiException(error_code=DiErrorCodes.NOT_READY)
            self._active_gets += 1
        path = tuple(frame for frame in self._resolution_path.get() if frame.is_current)
        frame = ExecutionFrame(key)
        token = self._resolution_path.set((*path, frame))
        try:
            if any(item.value == key for item in path):
                raise DiException(
                    error_code=DiErrorCodes.CIRCULAR_DEPENDENCY, msg=f"解析期间出现循环依赖：{key}"
                )
            self._validate_resolution(key)
            return cast(T, self._injector.get(key))
        finally:
            frame.active = False
            self._resolution_path.reset(token)
            with self._condition:
                self._active_gets -= 1
                if started is not None:
                    self._resolution_count += 1
                    self._resolution_seconds += perf_counter() - started
                self._condition.notify_all()

    def get_by_role(self, role: BaseEnum) -> tuple[object, ...]:
        """读取当前应用的活动角色实例，仍遵循各绑定的作用域。"""
        if self.state is not ContainerStateEnum.READY:
            raise DiException(error_code=DiErrorCodes.NOT_READY)
        return tuple(
            self.get(key)
            for key, binding in self._plan.bindings.items()
            if binding.metadata.role is role
        )

    def get_statistics(self) -> dict[str, object]:
        with self._condition:
            return {
                "state": self._state.value,
                "bindings": 0 if self._plan is None else len(self._plan.bindings),
                "singletons": len(self._created),
                "resolutions": self._resolution_count,
                "resolution_seconds": self._resolution_seconds,
                "configuration_revision": (
                    None if self._plan is None else self._plan.configuration_revision
                ),
            }

    def get_binding_diagnostics(self) -> tuple[BindingDiagnostic, ...]:
        """返回启动装配时每个候选的选择结果与原因；启动失败后仍可查询，不重新求值条件。"""
        with self._condition:
            selection = self._selection
        return () if selection is None else selection.diagnostics

    @staticmethod
    def _log_selection(selection: CandidateSelection) -> None:
        skipped = [
            item
            for item in selection.diagnostics
            if item.outcome is not BindingOutcomeEnum.SELECTED
        ]
        if not skipped:
            return
        logger.info(
            "DI 候选 {} 个，选中 {} 个，未绑定 {} 个；详情见 DiContainer.get_binding_diagnostics()",
            len(selection.diagnostics),
            len(selection.bindings),
            len(skipped),
        )
        for item in skipped:
            logger.debug(
                "DI 候选未绑定：{} -> {}（{}：{}）",
                item.component,
                item.key,
                item.outcome.label,
                item.reason,
            )

    def create_component(self, binding: ComponentBinding) -> object:
        """供原生 Injector Provider 调用，在关闭后禁止新建对象。"""
        if self.state not in {ContainerStateEnum.STARTING, ContainerStateEnum.READY}:
            raise DiException(error_code=DiErrorCodes.NOT_READY, msg="容器已停止接受新实例")
        plan = self._plan.dependencies[binding.implementation]
        args = [self.get(dependency) for _, dependency in plan.positional]
        kwargs = {name: self.get(dependency) for name, dependency in plan.keyword}
        try:
            instance = binding.implementation(*args, **kwargs)
        except Exception as error:
            raise DiException(
                msg=f"组件构造失败：{BindingPlan.qualified_name(binding.implementation)}",
                cause=error,
            ) from error
        if binding.scope is ComponentScopeEnum.SINGLETON:
            self._created.append((binding, instance))
        if plan.fields:
            instance.__di_resolver__ = self.get
            instance.__di_fields__ = dict(plan.fields)
        if binding.scope is ComponentScopeEnum.TRANSIENT:
            for name in self._plan.hooks[binding.implementation][LifecyclePhaseEnum.INITIALIZE]:
                result = getattr(instance, name)()
                if (
                    inspect.isawaitable(result)
                    or inspect.isgenerator(result)
                    or inspect.isasyncgen(result)
                ):
                    if inspect.iscoroutine(result):
                        result.close()
                    elif inspect.isgenerator(result):
                        result.close()
                    elif isinstance(result, asyncio.Future):
                        result.cancel()
                    raise DiException(
                        error_code=DiErrorCodes.INVALID_LIFECYCLE, msg="瞬态初始化必须同步完成"
                    )
        return instance

    def _validate_resolution(self, key: object) -> None:
        if key in self._instances or key in self.configuration.model_classes:
            return
        if key in self._plan.bindings:
            bindings = (self._plan.bindings[key],)
        elif key in self._plan.providers:
            bindings = self._plan.providers[key]
        else:
            raise DiException(
                error_code=DiErrorCodes.MISSING_BINDING,
                msg=(
                    f"未显式绑定依赖：{CandidateSelection.describe_key(key)}；"
                    f"{self._selection.explain(key)}"
                ),
            )
        for binding in bindings:
            if (
                binding.scope is ComponentScopeEnum.SINGLETON
                and binding.implementation not in self._ready_types
            ):
                raise DiException(
                    error_code=DiErrorCodes.NOT_READY,
                    msg=f"依赖尚未完成初始化：{BindingPlan.qualified_name(binding.implementation)}",
                )
            if (
                self.state is ContainerStateEnum.STOPPING
                and binding.scope is ComponentScopeEnum.TRANSIENT
            ):
                raise DiException(error_code=DiErrorCodes.NOT_READY, msg="关闭期间禁止创建瞬态依赖")

    async def shutdown(self) -> None:
        """等待唯一关闭任务；调用方取消或限时只放弃等待，销毁由容器持有的任务继续完成。"""
        if self._has_lifecycle_access() or any(
            frame.is_current for frame in self._resolution_path.get()
        ):
            raise DiException(
                error_code=DiErrorCodes.INVALID_LIFECYCLE,
                msg="生命周期或实例解析内部不能重入容器关闭",
            )
        with self._condition:
            if self._state is ContainerStateEnum.STARTING:
                raise DiException(
                    error_code=DiErrorCodes.NOT_READY, msg="请先取消并等待启动终态，再关闭容器"
                )
            if self._state is ContainerStateEnum.CLOSED:
                return
            if self._shutdown_task is None:
                self._state = ContainerStateEnum.STOPPING
                self._shutdown_task = asyncio.create_task(self._close(), name="DI shutdown")
                self._shutdown_task.add_done_callback(self._shutdown_finished)
        await asyncio.shield(self._shutdown_task)

    def _shutdown_finished(self, task: asyncio.Task) -> None:
        """消费关闭任务终态；独立使用的容器在此记录失败，有应用所有者时由应用汇总报告。"""
        if task.cancelled():
            return
        error = task.exception()
        if error is not None and self._application is None:
            logger.error(
                "DI 容器关闭发生错误：\n{}", "".join(ExceptionTraceFormatter.format(error))
            )

    async def _close(self) -> None:
        frame = ExecutionFrame(LifecyclePhaseEnum.DESTROY)
        token = self._lifecycle_context.set(frame)
        errors = []
        completed = False
        try:
            # 已开始的解析在工作线程内按 Condition 等待归零；线程内用户代码没有硬终止保证。
            if self._active_gets:
                await asyncio.to_thread(self._wait_for_resolutions)
            for binding, instance in reversed(self._created):
                for name in self._plan.hooks[binding.implementation][LifecyclePhaseEnum.DESTROY]:

                    async def destroy(target=instance, method=name):
                        await self._invoke_hook(target, method, LifecyclePhaseEnum.DESTROY)

                    error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                        destroy,
                        f"DI 销毁 {BindingPlan.qualified_name(binding.implementation)}.{name}",
                    )
                    if error is not None:
                        errors.append(error)
                    if cancellation is not None:
                        errors.append(cancellation)
                self._ready_types.discard(binding.implementation)
            completed = True
            if errors:
                raise BaseExceptionGroup("DI 资源清理失败", errors)
        finally:
            # 只有事件循环拆除会取消关闭任务本身；销毁未跑完时保持 STOPPING，不宣称 CLOSED。
            if completed:
                self._created.clear()
                self._ready_types.clear()
                self.state_manager.clear()
                self._instances.clear()
                self._injector = None
                with self._condition:
                    self._state = ContainerStateEnum.CLOSED
            frame.active = False
            self._lifecycle_context.reset(token)

    def _wait_for_resolutions(self) -> None:
        with self._condition:
            while self._active_gets:
                self._condition.wait()

    def _has_lifecycle_access(self) -> bool:
        frame = self._lifecycle_context.get()
        # 被钩子 await 的子任务可使用仍有效的阶段许可，钩子返回即共同失效。
        return frame is not None and frame.active

    @contextmanager
    def _lifecycle_access(self, phase: LifecyclePhaseEnum):
        frame = ExecutionFrame(phase)
        token = self._lifecycle_context.set(frame)
        try:
            yield
        finally:
            frame.active = False
            self._lifecycle_context.reset(token)

    async def _invoke_hook(self, instance: object, name: str, phase: LifecyclePhaseEnum) -> None:
        """超时采用协作取消，仍等待方法终态，不宣称能杀死任意用户代码。"""
        try:
            with self._lifecycle_access(phase):
                application_access = (
                    nullcontext()
                    if self._application is None
                    else self._application._phase_access(phase)
                )
                with application_access:
                    async with asyncio.timeout(self.settings.hook_timeout_seconds):
                        await LifecycleHooks.invoke(instance, name)
        except Exception as error:
            raise DiException(
                msg=f"组件生命周期失败：{BindingPlan.qualified_name(type(instance))}.{name}",
                cause=error,
            ) from error
