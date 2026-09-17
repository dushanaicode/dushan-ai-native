from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class ClearCacheByNameReqVO(BaseRequestVO):
    """管理后台 - 根据缓存名称清除缓存 Request VO"""

    key_prefix: Annotated[str, Field(..., description="缓存前缀")]
