from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO
from module_infra.controller.admin.server.vo.cpu_info_vo import CpuInfoVO
from module_infra.controller.admin.server.vo.memory_info_vo import MemoryInfoVO


class ServerUsageRespVO(BaseVO):
    """管理后台 - 服务监控精简信息 Response VO"""

    cpu: Annotated[CpuInfoVO, Field(description="CPU相关信息")]
    mem: Annotated[MemoryInfoVO, Field(description="內存相关信息")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "cpu": {"cpuNum": 8, "used": 30.5, "sys": 10.2, "free": 59.3},
                    "mem": {"total": "16GB", "used": "8GB", "free": "8GB", "usage": 50.0},
                }
            ]
        }
    }
