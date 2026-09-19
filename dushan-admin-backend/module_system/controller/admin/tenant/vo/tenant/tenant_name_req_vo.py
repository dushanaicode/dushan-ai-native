from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class TenantNameReqVO(BaseRequestVO):
    """管理后台 - 使用租户名获取租户编号 Request VO"""

    name: Annotated[str, Field(..., description="租户名", examples=["1024"])]
