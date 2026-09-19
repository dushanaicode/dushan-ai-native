from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class CacheKeysReqVO(PageQuery):
    """管理后台 - 缓存键名列表 Request VO"""

    key_prefix: Annotated[str, Field(..., description="缓存前缀")]
