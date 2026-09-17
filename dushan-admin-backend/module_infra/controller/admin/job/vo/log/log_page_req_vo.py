from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery


class JobLogPageReqVO(PageQuery):
    """管理后台 - 定时任务日志分页列表 Request VO"""

    job_id: Annotated[SnowflakeIdInput | None, Field(default=None, description="任务编号")]
    handler_name: Annotated[str | None, Field(default=None, description="处理器的名字，模糊匹配")]
    begin_time: Annotated[
        datetime | None, Field(default=None, exclude=True, description="开始执行时间")
    ]
    end_time: Annotated[
        datetime | None, Field(default=None, exclude=True, description="结束执行时间")
    ]
    status: Annotated[
        int | None, Field(default=None, description="任务状态，参见 JobLogStatusEnum 枚举")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "jobId": 10,
                    "handlerName": "sysUserSessionTimeoutJob",
                    "beginTime": "2020-05-20 05:20:00",
                    "endTime": "2020-05-20 13:14:00",
                    "status": 0,
                }
            ]
        }
    }
