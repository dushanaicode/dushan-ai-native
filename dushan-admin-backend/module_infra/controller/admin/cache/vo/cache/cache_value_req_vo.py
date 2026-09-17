from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class CacheValueReqVO(BaseRequestVO):
    """管理后台 - 缓存值查询 Request VO"""

    key_prefix: Annotated[str, Field(..., description="缓存前缀")]
    cache_key: Annotated[str, Field(..., description="缓存 key")]
