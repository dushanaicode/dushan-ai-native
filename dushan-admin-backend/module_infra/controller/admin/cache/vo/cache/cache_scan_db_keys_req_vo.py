from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class ScanDbKeysReqVO(BaseRequestVO):
    """管理后台 - 扫描 DB 键列表 Request VO"""

    db_name: Annotated[str, Field(..., description="DB 配置名称")]
    pattern: Annotated[str, Field("*", description="匹配模式")]
