from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class DeptDataPermissionRespDTO(BaseDTO):
    """部门数据权限 Response DTO"""

    all: Annotated[bool, Field(default=False, description="是否可查看全部数据")]
    self_only: Annotated[bool, Field(default=False, description="是否仅可查看自己的数据")]
    dept_ids: Annotated[
        set[int] | None, Field(default_factory=set, description="可查看的部门ID集合")
    ]
    user_ids: Annotated[
        set[int] | None, Field(default_factory=set, description="可查看的用户ID集合")
    ]
