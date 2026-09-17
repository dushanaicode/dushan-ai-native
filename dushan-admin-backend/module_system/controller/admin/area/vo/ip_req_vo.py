from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class IpReqVO(BaseRequestVO):
    """管理后台 - IP查询 Request VO"""

    ip: Annotated[str, Field(..., description="IP地址", examples=["127.0.0.1"])]
