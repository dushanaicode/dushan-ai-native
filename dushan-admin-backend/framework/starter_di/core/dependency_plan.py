import inspect
import sys
from dataclasses import dataclass
from typing import ForwardRef, NoReturn, get_args, get_origin

from framework.starter_di.decorators.inject import Inject
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

_RESOLUTION_ERRORS = (NameError, TypeError, ValueError, SyntaxError, AttributeError)


@dataclass(frozen=True, slots=True)
class DependencyPlan:
    """实例创建前只解析真正注入的构造参数与 Inject 字段类型，缺声明时明确失败。

    带默认值的参数、可变参数、返回注解以及没有 Inject 的类注解保留 Python 自身语义，
    即使只在 TYPE_CHECKING 下可见也不影响启动；每个注解按声明来源的命名空间求值。
    """

    positional: tuple[tuple[str, object], ...]
    keyword: tuple[tuple[str, object], ...]
    fields: tuple[tuple[str, object], ...]

    @classmethod
    def build(cls, component: type) -> "DependencyPlan":
        fields = cls._field_dependencies(component)
        positional, keyword = cls._constructor_dependencies(component)
        return cls(positional, keyword, fields)

    @classmethod
    def _field_dependencies(cls, component: type) -> tuple[tuple[str, object], ...]:
        fields = []
        for name, value in inspect.getmembers_static(component):
            if not isinstance(value, Inject):
                continue
            try:
                fields.append((name, cls._resolve_field(component, name)))
            except _RESOLUTION_ERRORS as error:
                cls._invalid(component, f"字段 {name}", error)
        if fields and not any("__dict__" in vars(owner) for owner in component.__mro__):
            cls._invalid(component, "字段注入", TypeError("字段 Inject 要求实例支持 __dict__"))
        return tuple(fields)

    @classmethod
    def _resolve_field(cls, component: type, name: str) -> object:
        """沿 MRO 找到声明该注解的类，用其所在模块和类命名空间求值。"""
        for owner in component.__mro__:
            annotations = inspect.get_annotations(owner)
            if name in annotations:
                module = sys.modules.get(owner.__module__)
                globalns = {} if module is None else vars(module)
                return cls._resolve_annotation(annotations[name], globalns, dict(vars(owner)))
        raise TypeError(f"Inject 字段缺少类型：{name}")

    @classmethod
    def _constructor_dependencies(
        cls, component: type
    ) -> tuple[tuple[tuple[str, object], ...], tuple[tuple[str, object], ...]]:
        constructor = component.__init__
        if constructor is object.__init__:
            return (), ()
        try:
            parameters = tuple(inspect.signature(constructor).parameters.values())[1:]
        except (TypeError, ValueError) as error:
            cls._invalid(component, "构造函数签名", error)
        globalns = getattr(inspect.unwrap(constructor), "__globals__", {})
        positional, keyword = [], []
        for parameter in parameters:
            if (
                parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}
                or parameter.default is not parameter.empty
            ):
                continue
            try:
                if parameter.annotation is parameter.empty:
                    raise TypeError("构造参数缺少类型")
                dependency = cls._resolve_annotation(parameter.annotation, globalns, None)
            except _RESOLUTION_ERRORS as error:
                cls._invalid(component, f"构造参数 {parameter.name}", error)
            target = positional if parameter.kind is parameter.POSITIONAL_ONLY else keyword
            target.append((parameter.name, dependency))
        return tuple(positional), tuple(keyword)

    @classmethod
    def _resolve_annotation(
        cls, annotation: object, globalns: dict, localns: dict | None
    ) -> object:
        """字符串注解按 typing.get_type_hints 的求值规则处理，但只针对当前注入点。"""
        annotation = cls._evaluate(annotation, globalns, localns)
        if get_origin(annotation) is list and len(get_args(annotation)) == 1:
            annotation = list[cls._evaluate(get_args(annotation)[0], globalns, localns)]
        return cls._validate_type(annotation)

    @staticmethod
    def _evaluate(value: object, globalns: dict, localns: dict | None) -> object:
        seen: set[str] = set()
        while isinstance(value, (str, ForwardRef)):
            expression = value if isinstance(value, str) else value.__forward_arg__
            if expression in seen:
                raise TypeError(f"注解字符串循环引用：{expression}")
            seen.add(expression)
            value = eval(expression, globalns, localns)
        return value

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

    @staticmethod
    def _invalid(component: type, target: str, error: Exception) -> NoReturn:
        raise DiException(
            error_code=DiErrorCodes.INVALID_DEFINITION,
            msg=(
                f"无法解析组件依赖：{component.__module__}.{component.__qualname__} {target} "
                f"({type(error).__name__}: {error})"
            ),
            cause=error,
        ) from error

    @property
    def dependencies(self) -> tuple[object, ...]:
        return tuple(
            dependency for _, dependency in (*self.positional, *self.keyword, *self.fields)
        )
