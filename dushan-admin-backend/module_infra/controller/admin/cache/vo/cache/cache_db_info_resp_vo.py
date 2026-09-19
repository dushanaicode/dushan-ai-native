from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class CacheDbInfoRespVO(BaseVO):
    """管理后台 - Redis DB 信息 Response VO"""

    name: Annotated[str, Field(..., description="DB 配置名称")]
    db_index: Annotated[int, Field(..., description="DB 索引号")]
    label: Annotated[str, Field(..., description="DB 显示标签")]
    key_count: Annotated[int, Field(0, description="key 数量")]
