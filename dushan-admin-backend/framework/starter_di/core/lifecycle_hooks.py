import inspect

from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.definitions.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_exception import DiException


class LifecycleHooks:
    """静态收集约定方法和显式标记方法，不求值描述符。"""

    @staticmethod
    def collect(component: type, phase: LifecyclePhaseEnum) -> tuple[str, ...]:
        names = []
        for name, method in inspect.getmembers_static(component):
            if name != phase.value and not (
                inspect.isfunction(method) and vars(method).get("__di_lifecycle__") is phase
            ):
                continue
            if (
                not inspect.isfunction(method)
                or inspect.isgeneratorfunction(method)
                or inspect.isasyncgenfunction(method)
            ):
                raise DiException(
                    error_code=DiErrorCodes.INVALID_LIFECYCLE,
                    msg=f"生命周期必须是普通同步或异步实例方法：{component.__module__}.{component.__qualname__}.{name}",
                )
            try:
                signature = inspect.signature(method)
                if len(signature.parameters) != 1:
                    raise TypeError("生命周期只能接收 self")
                signature.bind(object())
            except TypeError as error:
                raise DiException(
                    error_code=DiErrorCodes.INVALID_LIFECYCLE,
                    msg=f"生命周期必须能绑定 self 后无参调用：{component.__qualname__}.{name}",
                    cause=error,
                ) from error
            names.append(name)
        return tuple(sorted(names, key=lambda name: (name != phase.value, name)))

    @staticmethod
    async def invoke(instance: object, name: str) -> None:
        """异步启动/清理阶段接受同步方法或 awaitable 返回值。"""
        result = getattr(instance, name)()
        if inspect.isgenerator(result) or inspect.isasyncgen(result):
            if inspect.isgenerator(result):
                result.close()
            else:
                await result.aclose()
            raise DiException(
                error_code=DiErrorCodes.INVALID_LIFECYCLE, msg="生命周期不能返回生成器"
            )
        if inspect.isawaitable(result):
            await result
