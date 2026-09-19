from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from framework.common.schemas.base_bo import BaseBO
from framework.starter_cache.definitions.enums.cache_generation_state_enum import (
    CacheGenerationStateEnum,
)

type GenerationText = Annotated[str, StringConstraints(strict=True, min_length=1)]


class CacheGenerationState(BaseBO):
    """一个 generation 栅栏键的原子状态快照。

    epoch 区分 Redis 实例被清空后重建的同名键，version 每次失效自增，
    state 表示失效是否已经完成；三者共同决定一次回源发布是否仍然有效。
    """

    model_config = ConfigDict(frozen=True)

    generation_key: GenerationText
    epoch: GenerationText
    version: int = Field(strict=True, ge=0)
    state: CacheGenerationStateEnum
