from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from module_infra.definitions.enums.job.job_status_enum import JobStatusEnum


class JobRespVO(BaseVO):
    """管理后台 - 定时任务信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="任务编号"), ExcelColumn(title="任务编号")]
    name: Annotated[str, Field(..., description="任务名称"), ExcelColumn(title="任务名称")]
    status: Annotated[
        int,
        Field(..., description="任务状态"),
        ExcelColumn(title="任务状态", converter=EnumConverter(JobStatusEnum)),
    ]
    handler_name: Annotated[
        str, Field(..., description="处理器的名字"), ExcelColumn(title="处理器的名字")
    ]
    handler_param: Annotated[
        str | None,
        Field(default=None, description="处理器的参数"),
        ExcelColumn(title="处理器的参数"),
    ]
    cron_expression: Annotated[
        str, Field(..., description="CRON 表达式"), ExcelColumn(title="CRON 表达式")
    ]
    retry_count: Annotated[int, Field(..., description="重试次数")]
    retry_interval: Annotated[int, Field(..., description="重试间隔")]
    monitor_timeout: Annotated[
        int | None,
        Field(default=None, description="监控超时时间"),
        ExcelColumn(title="监控超时时间"),
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "测试任务",
                    "status": 0,
                    "handlerName": "sysUserSessionTimeoutJob",
                    "handlerParam": "dushan",
                    "cronExpression": "0/10 * * * * *",
                    "retryCount": 3,
                    "retryInterval": 1000,
                    "monitorTimeout": 1000,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
