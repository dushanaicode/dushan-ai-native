from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class TenantPackageRespDTO(BaseDTO):
    """租户套餐 Response DTO（跨模块传输）"""

    id: Annotated[int, Field(..., description="套餐编号")]
    name: Annotated[str, Field(..., description="套餐名")]
    status: Annotated[int, Field(..., description="状态")]
    quota_config: Annotated[dict | None, Field(None, description="通用配额模板（JSON）")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "VIP",
                    "status": 0,
                    "quotaConfig": {"ai": {"enabled": True, "monthlyTokenLimit": 500000}},
                }
            ]
        }
    }
