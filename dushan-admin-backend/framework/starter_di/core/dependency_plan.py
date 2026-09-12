import inspect
from dataclasses import dataclass
from typing import get_args, get_origin, get_type_hints

from framework.starter_di.decorators.inject import Inject
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


@dataclass(frozen=True, slots=True)
class DependencyPlan:
    """实例创建前解析构造参数和字段类型，缺声明时明确失败。"""

    positional: tuple[tuple[str, object], ...]
    keyword: tuple[tuple[str, object], ...]
    fields: tuple[tuple[str, object], ...]

    @classmethod
    def build(cls, component: type) -> "DependencyPlan":
        positional, keyword, fields = [], [], []
        try:
            descriptors = tuple(
                (name, value)
                for name, value in inspect.getmembers_static(component)
                if isinstance(value, Inject)
            )
            annotations = get_type_hints(component) if descriptors else {}
            for name, _descriptor in descriptors:
                if name not in annotations:
                    raise TypeError(f"Inject 字段缺少类型：{name}")
                fields.append((name, cls._validate_type(annotations[name])))
            if fields and not any("__dict__" in vars(owner) for owner in component.__mro__):
                raise TypeError("字段 Inject 要求实例支持 __dict__")
            constructor = component.__init__
            if constructor is not object.__init__:
                hints = get_type_hints(constructor)
                parameters = tuple(inspect.signature(constructor).parameters.values())[1:]
                for parameter in parameters:
                    if (
                        parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}
                        or parameter.default is not parameter.empty
                    ):
                        continue
                    if parameter.name not in hints:
                        raise TypeError(f"构造参数缺少类型：{parameter.name}")
                    dependency = cls._validate_type(hints[parameter.name])
                    target = positional if parameter.kind is parameter.POSITIONAL_ONLY else keyword
                    target.append((parameter.name, dependency))
        except (NameError, TypeError, ValueError) as error:
            raise DiException(
                error_code=DiErrorCodes.INVALID_DEFINITION,
                msg=f"无法解析组件依赖：{component.__module__}.{component.__qualname__} ({type(error).__name__})",
                cause=error,
            ) from error
        return cls(tuple(positional), tuple(keyword), tuple(fields))

    @staticmethod
    def _validate_type(value: object) -> object:
        if isinstance(value, type):
            return value
        if (
            get_origin(value) is list
            and len(get_args(value)) == 1
            and isinstance(get_args(value)[0], type)
        ):
            return list[get_args(value)[0]]
        raise TypeError("依赖必须是明确类型或 list[接口类型]")

    @property
    def dependencies(self) -> tuple[object, ...]:
        return tuple(
            dependency for _, dependency in (*self.positional, *self.keyword, *self.fields)
        )
