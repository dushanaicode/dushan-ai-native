from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class RoleMenuReqVO(BaseRequestVO):
    """管理后台 - 获得角色拥有的菜单编号 Request VO"""

    role_id: Annotated[
        SnowflakeIdInput, Field(..., alias="roleId", description="角色编号", examples=[1024])
    ]
