from typing import Self

from pydantic import ConfigDict, Field, model_validator

from framework.common.schemas.base_bo import BaseBO


class CacheReadResult[T](BaseBO):
    """一次缓存读取的明确结果；命中的 null 与未命中是两种不同状态。

    调用方必须先看 hit 再取 value，不能用 value is None 判断未命中，
    否则防穿透写入的空值会被当成 miss 反复回源。
    """

    model_config = ConfigDict(frozen=True)

    hit: bool = Field(strict=True)
    value: T | None = None

    @model_validator(mode="after")
    def validate_miss_value(self) -> Self:
        """未命中不允许携带值；命中的 None 是合法的空值缓存。"""
        if not self.hit and self.value is not None:
            raise ValueError("缓存未命中不能携带值")
        return self
