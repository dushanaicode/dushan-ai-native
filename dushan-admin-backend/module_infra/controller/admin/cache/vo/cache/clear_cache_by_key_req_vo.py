from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class ClearCacheByKeyReqVO(BaseRequestVO):
    """管理后台 - 根据缓存键名清除缓存 Request VO"""

    cache_key_pattern: Annotated[str, Field(..., description="缓存 key")]
