import hashlib
import inspect
import json
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from framework.starter_cache.exception.cache_config_exception import CacheConfigException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes


class KeyBuilder:
    """把函数参数渲染成稳定的缓存标识，模板语法是 {{参数名}}。

    模板在装饰阶段就校验：只允许引用函数的直接参数，不支持属性访问和表达式，
    这样键的取值范围在部署前就是确定的，不会因为某次调用传入意外对象而变形。
    容器类型参数用规范化 token 求摘要，保证同一份数据在不同进程得到同一个键。
    """

    PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")

    @staticmethod
    @lru_cache(maxsize=256)
    def get_signature(func: Callable) -> inspect.Signature:
        """缓存函数签名，装饰阶段与调用阶段共用同一份。"""
        return inspect.signature(func)

    @classmethod
    def validate_template(cls, func: Callable, template: str | None) -> inspect.Signature:
        """在装饰阶段校验模板，返回复用的签名。"""
        signature = cls.get_signature(func)
        if template is None:
            return signature
        if not isinstance(template, str) or not template:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=f"{func.__qualname__} 的缓存键模板必须是非空字符串",
            )
        residual = cls.PLACEHOLDER_PATTERN.sub("", template)
        if "{{" in residual or "}}" in residual:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=f"{func.__qualname__} 的缓存键模板包含不支持的占位符：{template}",
            )
        parameters = cls._parameter_names(signature)
        unknown = sorted(set(cls.PLACEHOLDER_PATTERN.findall(template)) - set(parameters))
        if unknown:
            raise CacheConfigException(
                error_code=CacheErrorCodes.INVALID_CACHE_KEY,
                msg=(
                    f"{func.__qualname__} 的缓存键模板引用了未知参数 {unknown}；"
                    f"可用参数：{parameters}"
                ),
            )
        return signature

    @classmethod
    def build_identifier(
        cls,
        template: str | None,
        func: Callable,
        signature: inspect.Signature,
        args: tuple,
        kwargs: dict,
    ) -> str:
        """渲染本次调用的缓存标识；没有模板时按函数名和全部参数生成。"""
        arguments = cls.bind_arguments(signature, args, kwargs)
        if template is None:
            parts = [func.__name__]
            parts.extend(
                f"{name}={cls.serialize_value(value)}" for name, value in arguments.items()
            )
            return ":".join(parts)
        result = template
        for placeholder in cls.PLACEHOLDER_PATTERN.findall(template):
            result = result.replace(
                f"{{{{{placeholder}}}}}", cls.serialize_value(arguments[placeholder])
            )
        return result

    @classmethod
    def bind_arguments(
        cls, signature: inspect.Signature, args: tuple, kwargs: dict
    ) -> dict[str, Any]:
        """按签名统一位置参数、关键字参数和默认值，并去掉 self/cls。"""
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        arguments = dict(bound.arguments)
        names = list(signature.parameters)
        if names and names[0] in ("self", "cls"):
            arguments.pop(names[0], None)
        return arguments

    @staticmethod
    def _parameter_names(signature: inspect.Signature) -> list[str]:
        """返回模板可引用的参数名，不含 self/cls。"""
        names = list(signature.parameters)
        if names and names[0] in ("self", "cls"):
            return names[1:]
        return names

    @classmethod
    def serialize_value(cls, value: Any) -> str:
        """把参数转成键片段；容器类型取规范化摘要，避免键过长或顺序不稳定。"""
        if value is None:
            return "none"
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, tuple, set, frozenset, dict)):
            digest = hashlib.sha256(cls._canonical_token(value).encode("utf-8")).hexdigest()[:16]
            return f"{type(value).__name__}:{digest}"
        raise CacheConfigException(
            error_code=CacheErrorCodes.INVALID_CACHE_KEY,
            msg=f"缓存键参数不支持类型 {type(value).__name__}",
        )

    @classmethod
    def _canonical_token(cls, value: Any) -> str:
        """生成跨进程稳定且区分类型的 token：1 和 True、1 和 "1" 不会得到同一个键。"""
        if value is None:
            return "none"
        if isinstance(value, bool):
            return f"bool:{str(value).lower()}"
        if isinstance(value, int):
            return f"int:{value}"
        if isinstance(value, float):
            return f"float:{value.hex()}"
        if isinstance(value, str):
            return f"str:{json.dumps(value, ensure_ascii=True)}"
        if isinstance(value, list):
            return "list:[" + ",".join(cls._canonical_token(item) for item in value) + "]"
        if isinstance(value, tuple):
            return "tuple:[" + ",".join(cls._canonical_token(item) for item in value) + "]"
        if isinstance(value, set):
            return "set:[" + ",".join(sorted(cls._canonical_token(item) for item in value)) + "]"
        if isinstance(value, frozenset):
            members = sorted(cls._canonical_token(item) for item in value)
            return "frozenset:[" + ",".join(members) + "]"
        if isinstance(value, dict):
            items = sorted(
                (cls._canonical_token(key), cls._canonical_token(item))
                for key, item in value.items()
            )
            return "dict:{" + ",".join(f"{key}={item}" for key, item in items) + "}"
        raise CacheConfigException(
            error_code=CacheErrorCodes.INVALID_CACHE_KEY,
            msg=f"缓存键容器成员不支持类型 {type(value).__name__}",
        )
