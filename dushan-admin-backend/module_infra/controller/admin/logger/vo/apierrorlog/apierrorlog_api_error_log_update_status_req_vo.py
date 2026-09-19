from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class ApiErrorLogUpdateStatusReqVO(BaseRequestVO):
    """管理后台 - API 错误日志更新处理状态 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="日志编号")]
    process_status: Annotated[int, Field(..., description="处理状态")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "processStatus": 1}]}}
