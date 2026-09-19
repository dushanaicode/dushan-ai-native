from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class JobUpdateStatusReqVO(BaseRequestVO):
    """管理后台 - 定时任务更新状态 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="任务编号")]
    status: Annotated[int, Field(..., description="状态")]
