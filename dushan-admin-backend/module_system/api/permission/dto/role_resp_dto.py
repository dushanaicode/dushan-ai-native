from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class RoleRespDTO(BaseDTO):
    """角色 Response DTO"""

    id: Annotated[int, Field(..., description="角色编号")]
    name: Annotated[str, Field(..., description="角色名称")]
    code: Annotated[str, Field(..., description="角色编码")]
    sort: Annotated[int, Field(..., description="显示顺序")]
    status: Annotated[int, Field(..., description="角色状态")]
