from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class CacheKeyDetailRespVO(BaseVO):
    """管理后台 - 缓存键详情 Response VO"""

    key: Annotated[str, Field(..., description="完整 Redis key")]
    key_type: Annotated[str, Field(..., description="Redis 数据类型 (string/hash/list/set/zset)")]
    ttl: Annotated[int, Field(..., description="TTL(秒)，-1 表示永不过期，-2 表示不存在")]
    db_name: Annotated[str, Field(..., description="所属 DB 配置名")]
    value: Annotated[str | None, Field(None, description="键值内容（仅 string 类型）")]
    size: Annotated[int | None, Field(None, description="元素数量（非 string 类型）")]
