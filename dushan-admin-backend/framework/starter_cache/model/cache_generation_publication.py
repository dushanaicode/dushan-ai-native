from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from framework.common.schemas.base_bo import BaseBO
from framework.starter_cache.model.cache_generation_state import CacheGenerationState

type OwnerToken = Annotated[str, StringConstraints(strict=True, min_length=32, max_length=32)]
type GenerationToken = Annotated[str, StringConstraints(strict=True, min_length=64, max_length=64)]
type SerializedPayload = Annotated[str, StringConstraints(strict=True, min_length=1)]


class CacheGenerationPublication(BaseBO):
    """回源写入 Redis 的信封：携带写入者身份与当时的 generation 快照。

    owner_token 让补偿删除只会删掉自己写的那一份值，generation_snapshot 让读侧
    可以判断这份值是否已经被之后的失效作废。payload 用 base64 保存，避免与信封混淆。
    """

    model_config = ConfigDict(frozen=True)

    owner_token: OwnerToken
    generation_token: GenerationToken
    generation_snapshot: tuple[CacheGenerationState, ...] = Field(min_length=1)
    payload_base64: SerializedPayload
