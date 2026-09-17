from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class PostRespDTO(BaseDTO):
    """岗位 Response DTO"""

    id: Annotated[int, Field(..., description="岗位序号")]
    name: Annotated[str, Field(..., description="岗位名称")]
    code: Annotated[str, Field(..., description="岗位编码")]
    sort: Annotated[int, Field(..., description="岗位排序")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1024, "name": "渡山", "code": "dushan", "sort": 1, "status": 0}]
        }
    }
