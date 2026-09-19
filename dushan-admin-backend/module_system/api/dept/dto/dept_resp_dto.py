from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class DeptRespDTO(BaseDTO):
    """部门 Response DTO"""

    id: Annotated[int, Field(..., description="部门编号")]
    name: Annotated[str, Field(..., description="部门名称")]
    parent_id: Annotated[int, Field(..., description="父部门编号")]
    leader_user_id: Annotated[int, Field(..., description="负责人的用户编号")]
    status: Annotated[int, Field(..., description="部门状态，参见 StatusEnum 枚举类")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"id": 1024, "name": "渡山技术部", "parentId": 1, "leaderUserId": 1024, "status": 0}
            ]
        }
    }
