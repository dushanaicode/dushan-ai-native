from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class DeleteKeyReqVO(BaseRequestVO):
    """管理后台 - 删除缓存键 Request VO"""

    db_name: Annotated[str, Field(..., description="DB 配置名称")]
    key: Annotated[str, Field(..., description="Redis key")]
