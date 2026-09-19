from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class TenantWebsiteReqVO(BaseRequestVO):
    """管理后台 - 使用网站获取租户 Request VO"""

    website: Annotated[str, Field(..., description="网站")]
