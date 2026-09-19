from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class PermissionUserRoleReqVO(BaseRequestVO):
    """管理后台 - 获得管理员拥有的角色编号列表 Request VO"""

    user_id: Annotated[
        SnowflakeIdInput, Field(..., alias="userId", description="用户编号", examples=[666])
    ]
