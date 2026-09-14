import ast
import re
from collections.abc import Mapping
from enum import Enum
from uuid import UUID

from framework.common.security.sanitizer import Sanitizer


class BusinessAttributes:
    """按明确参数路径读取标识，或使用标量字面量；不序列化整个参数或任意对象。"""

    @staticmethod
    def validate(expression: str) -> None:
        if not expression:
            return
        if len(expression) > 256:
            raise ValueError("业务标识表达式过长")
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){0,7}", expression):
            return
        value = ast.literal_eval(expression)
        if type(value) not in (str, int, float, bool, type(None)):
            raise ValueError("业务标识只接受参数点路径或标量字面量")

    @staticmethod
    def read(expression: str, arguments):
        if not expression:
            return None
        if expression in {"True", "False", "None"} or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*){0,7}", expression
        ):
            return ast.literal_eval(expression)
        path = expression.split(".")
        if any(
            Sanitizer.sanitize_sensitive_data({part: "probe"})[part] != "probe" for part in path
        ):
            return None
        value = arguments[path[0]]
        for name in path[1:]:
            value = value[name] if isinstance(value, Mapping) else getattr(value, name)
        if isinstance(value, Enum):
            value = value.value
        if isinstance(value, UUID):
            return str(value)
        return value if type(value) in (str, int, float, bool, type(None)) else None

    @staticmethod
    def arguments(signature, args, kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        return bound.arguments
