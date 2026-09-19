from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from framework.common.schemas import BaseDTO


class MenuRespDTO(BaseDTO):
    """菜单 Response DTO"""

    id: Annotated[int, Field(..., description="菜单编号")]
    name: Annotated[str, Field(..., description="菜单名称")]
    permission: Annotated[str, Field(default="", description="权限标识")]
    kind: Literal["group", "page", "action", "link", "iframe"]
    status: Annotated[int, Field(..., description="状态（0-启用 1-禁用）")]
    parent_id: Annotated[int, Field(default=0, description="父菜单编号")]
    url: str | None = None
    data_permission: bool = False
