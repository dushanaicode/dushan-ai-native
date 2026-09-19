from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class DataSourceConfigStatusReqVO(BaseRequestVO):
    """管理后台 - 根据状态获得数据源配置列表 Request VO"""

    status: Annotated[int, Field(..., description="状态")]
