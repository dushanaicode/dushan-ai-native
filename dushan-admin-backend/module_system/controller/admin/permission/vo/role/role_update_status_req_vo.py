from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class RoleUpdateStatusReqVO(BaseRequestVO):
    """管理后台 - 角色状态更新 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="角色编号")]
    status: Annotated[int, Field(..., description="状态")]
