from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas import BaseVO


class CacheInfoRespVO(BaseVO):
    """管理后台 - 缓存信息 Response VO"""

    cache_key: Annotated[str | None, Field(description="缓存键名")] = None
    cache_name: Annotated[str | None, Field(description="缓存名称")] = None
    cache_value: Annotated[Any | None, Field(description="缓存内容")] = None
