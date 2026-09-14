import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, SecretBytes, SecretStr

from framework.starter_protection.subject.protection_subject import ProtectionSubject


class ProtectionKey:
    """规范化已校验参数，类型保真且不把身份、密钥或业务原文放进 Redis 键。"""

    @classmethod
    def build(
        cls, operation: str, subject: ProtectionSubject, parameters: object, limit: int
    ) -> str:
        if not operation or len(operation) > 256:
            raise ValueError("保护操作名称长度必须为 1–256")
        encoded = cls.json(cls.normalize([operation, subject, parameters])).encode("utf-8")
        if len(encoded) > limit:
            raise ValueError("保护参数规范编码超出长度上限")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def json(value: object) -> str:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        )

    @classmethod
    def normalize(cls, value: object, depth: int = 0) -> object:
        # 调用输入的结构边界；同时拒绝循环容器，避免递归耗尽进程栈。
        if depth > 32:
            raise ValueError("保护参数嵌套超过 32 层或存在循环")
        if value is None or type(value) in (str, bool, int):
            return [type(value).__name__, value]
        if type(value) is float:
            if not math.isfinite(value):
                raise ValueError("保护参数不能含非有限浮点数")
            return ["float", value.hex()]
        if isinstance(value, Enum):
            return ["enum", cls.name(value), cls.normalize(value.value, depth + 1)]
        if isinstance(value, (SecretStr, SecretBytes)):
            return [cls.name(value), cls.normalize(value.get_secret_value(), depth + 1)]
        if isinstance(value, bytes):
            return ["bytes", value.hex()]
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("保护参数不能含非有限 Decimal")
            sign, digits, exponent = value.as_tuple()
            digits = list(digits)
            while len(digits) > 1 and digits[-1] == 0:
                digits.pop()
                exponent += 1
            return ["decimal", sign, digits, exponent] if any(digits) else ["decimal", 0]
        if isinstance(value, (datetime, date, time)):
            return [type(value).__name__, value.isoformat()]
        if isinstance(value, (UUID, Path)):
            return [cls.name(value), str(value)]
        if isinstance(value, BaseModel):
            # 读取字段本身，避免序列化器将 SecretStr 都改成同一个掩码。
            values = {name: getattr(value, name) for name in type(value).model_fields}
            if value.model_extra is not None:
                values.update(value.model_extra)
            return ["model", cls.name(value), cls.normalize(values, depth + 1)]
        if is_dataclass(value) and not isinstance(value, type):
            values = {field.name: getattr(value, field.name) for field in fields(value)}
            return ["dataclass", cls.name(value), cls.normalize(values, depth + 1)]
        if isinstance(value, Mapping):
            entries = [
                [cls.normalize(k, depth + 1), cls.normalize(v, depth + 1)] for k, v in value.items()
            ]
            return ["mapping", sorted(entries, key=lambda item: cls.json(item[0]))]
        if isinstance(value, (list, tuple, set, frozenset)):
            items = [cls.normalize(item, depth + 1) for item in value]
            if isinstance(value, (set, frozenset)):
                items.sort(key=cls.json)
            return [type(value).__name__, items]
        raise TypeError("不支持该保护参数类型；请显式选择业务字段")

    @staticmethod
    def name(value: object) -> str:
        return f"{type(value).__module__}.{type(value).__qualname__}"
