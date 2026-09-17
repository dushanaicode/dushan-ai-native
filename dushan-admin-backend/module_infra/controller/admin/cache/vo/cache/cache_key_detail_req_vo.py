from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class KeyDetailReqVO(BaseRequestVO):
    """管理后台 - 缓存键详情查询 Request VO"""

    db_name: Annotated[str, Field(..., description="DB 配置名称")]
    key: Annotated[str, Field(..., description="Redis key")]
