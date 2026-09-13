import json
from typing import Any

from pydantic import BaseModel

from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_serialization_exception import (
    CacheSerializationException,
)
from framework.starter_di.decorators.components import framework


@framework
class CacheSerializer:
    """只接受明确 JSON 值和 Pydantic 模型的缓存序列化器。

    刻意不支持 pickle：缓存内容可能被同一个 Redis 上的其他进程写入，
    反序列化必须不能执行任意对象构造。NaN/Infinity 也被拒绝，
    因为它们不是合法 JSON，写入后其他语言的消费者无法解析。
    """

    @staticmethod
    def _to_json_value(value: Any) -> Any:
        """把 Pydantic 模型和集合转成 JSON 可表达的形式，其余类型明确失败。"""
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, (set, frozenset)):
            return sorted(value, key=repr)
        raise TypeError(f"缓存不支持的值类型: {type(value).__name__}")

    @staticmethod
    def _reject_non_finite(value: str) -> None:
        """JSON 中的 NaN/Infinity 字面量一律拒绝，不静默转换成 None。"""
        raise ValueError(f"缓存不接受非有限数字: {value}")

    def serialize(self, value: Any) -> bytes:
        """序列化为 UTF-8 JSON 字节串。"""
        try:
            payload = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                default=self._to_json_value,
                separators=(",", ":"),
            )
            return payload.encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as error:
            raise CacheSerializationException(
                error_code=CacheErrorCodes.SERIALIZATION_FAILED,
                msg="缓存对象序列化失败",
                cause=error,
            ) from error

    def deserialize(self, raw: str | bytes) -> Any:
        """把 Redis 返回的字节或字符串还原为 Python 值。"""
        try:
            payload = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            if not isinstance(payload, str):
                raise TypeError("缓存反序列化只接受 str 或 bytes")
            return json.loads(payload, parse_constant=self._reject_non_finite)
        except (TypeError, ValueError, UnicodeError) as error:
            raise CacheSerializationException(
                error_code=CacheErrorCodes.DESERIALIZATION_FAILED,
                msg="缓存数据反序列化失败",
                cause=error,
            ) from error
