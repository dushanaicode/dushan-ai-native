from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO


class CpuInfoVO(BaseVO):
    """管理后台 - CPU 信息 VO"""

    cpu_num: Annotated[int | None, Field(description="核心数")] = None
    used: Annotated[float | None, Field(description="CPU用户使用率")] = None
    sys: Annotated[float | None, Field(description="CPU系统使用率")] = None
    free: Annotated[float | None, Field(description="CPU当前空闲率")] = None
    model_config = {
        "json_schema_extra": {"examples": [{"cpuNum": 8, "used": 30.5, "sys": 10.2, "free": 59.3}]}
    }
