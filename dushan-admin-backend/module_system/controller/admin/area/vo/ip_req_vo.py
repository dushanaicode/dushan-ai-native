from typing import Annotated

from pydantic import Field, field_validator

from framework.common.schemas import BaseRequestVO
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver


class IpReqVO(BaseRequestVO):
    """管理后台 - IP查询 Request VO"""

    ip: Annotated[str, Field(..., description="IP地址", examples=["127.0.0.1"])]

    @field_validator("ip")
    @classmethod
    def normalize_ip(cls, value: str) -> str:
        normalized = ClientIpResolver.normalize_ip(value)
        if normalized is None:
            raise ValueError("IP地址无效")
        return normalized
