from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class JobNextTimesReqVO(BaseRequestVO):
    """管理后台 - 获得定时任务的下 n 次执行时间 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="任务编号")]
    count: Annotated[int, Field(5, description="数量")]
