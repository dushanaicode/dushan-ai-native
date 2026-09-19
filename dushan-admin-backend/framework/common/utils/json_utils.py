import json
import math
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T")
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


class JsonUtils:
    """处理严格 JSON 和 Pydantic 模型；解析失败直接抛错，不转换为空结果。"""

    @staticmethod
    def to_json(obj: object, indent: int | None = None) -> str:
        """生成 UTF-8 可表示的标准 JSON，未知对象和非有限数值直接报错。"""
        value = obj.model_dump(mode="json") if isinstance(obj, BaseModel) else obj
        return json.dumps(value, ensure_ascii=False, indent=indent, allow_nan=False)

    @classmethod
    def to_json_bytes(cls, obj: object) -> bytes:
        """生成 UTF-8 JSON 字节。"""
        return cls.to_json(obj).encode("utf-8")

    @classmethod
    def loads(cls, data: str | bytes) -> JsonValue:
        """拒绝重复键、NaN、Infinity 和浮点溢出，避免解析结果存在歧义。"""
        return json.loads(
            data,
            object_pairs_hook=cls._unique_object,
            parse_constant=cls._reject_constant,
            parse_float=cls._finite_float,
        )

    @staticmethod
    def _unique_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
        """发现同一对象的重复键立即报错，不让后值覆盖前值。"""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("JSON 对象存在重复键")
            result[key] = value
        return result

    @staticmethod
    def _reject_constant(value: str) -> float:
        """拒绝 JSON 标准不允许的数值常量。"""
        raise ValueError("JSON 不允许非有限数值")

    @staticmethod
    def _finite_float(value: str) -> float:
        """解析浮点数并拒绝指数导致的无穷大。"""
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON 浮点数超出有限范围")
        return number

    @classmethod
    def parse_obj(cls, data: str | bytes, model: type[T]) -> T:
        """按明确的目标类型校验解析结果；空内容仍是非法 JSON。"""
        return TypeAdapter(model).validate_python(cls.loads(data))

    @classmethod
    def parse_list(cls, data: str | bytes, model: type[T]) -> list[T]:
        """校验 JSON 数组及每个成员。"""
        return TypeAdapter(list[model]).validate_python(cls.loads(data))

    @staticmethod
    def get_by_path(json_obj: dict[str, JsonValue], path: str) -> JsonValue:
        """读取点分字典路径；缺键或中间层不是对象时报错，合法空值原样返回。"""
        if not path:
            raise ValueError("JSON 路径不能为空")
        current = json_obj
        for part in path.split("."):
            current = current[part]
        return current

    @classmethod
    def is_valid_json(cls, text: str) -> bool:
        """判断文本能否按严格 JSON 契约解析。"""
        try:
            cls.loads(text)
        except ValueError:
            return False
        return True
