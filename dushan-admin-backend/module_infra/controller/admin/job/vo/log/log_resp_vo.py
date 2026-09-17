from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from module_infra.definitions.enums.job.job_log_status_enum import JobLogStatusEnum


class JobLogRespVO(BaseVO):
    """管理后台 - 定时任务日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="日志编号"), ExcelColumn(title="日志编号")]
    job_id: Annotated[
        SnowflakeIdStr, Field(..., description="任务编号"), ExcelColumn(title="任务编号")
    ]
    handler_name: Annotated[
        str, Field(..., description="处理器的名字"), ExcelColumn(title="处理器的名字")
    ]
    handler_param: Annotated[
        str | None,
        Field(default=None, description="处理器的参数"),
        ExcelColumn(title="处理器的参数"),
    ]
    execute_index: Annotated[
        int, Field(..., description="第几次执行"), ExcelColumn(title="第几次执行")
    ]
    begin_time: Annotated[
        datetime, Field(..., description="开始执行时间"), ExcelColumn(title="开始执行时间")
    ]
    end_time: Annotated[
        datetime | None,
        Field(default=None, description="结束执行时间"),
        ExcelColumn(title="结束执行时间"),
    ]
    duration: Annotated[
        int | None, Field(default=None, description="执行时长"), ExcelColumn(title="执行时长")
    ]
    status: Annotated[
        int,
        Field(..., description="任务状态，参见 JobLogStatusEnum 枚举"),
        ExcelColumn(title="任务状态", converter=EnumConverter(JobLogStatusEnum)),
    ]
    result: Annotated[
        str | None, Field(default=None, description="结果数据"), ExcelColumn(title="结果数据")
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "jobId": 1024,
                    "handlerName": "sysUserSessionTimeoutJob",
                    "handlerParam": "dushan",
                    "executeIndex": 1,
                    "beginTime": "2020-05-20 05:20:00",
                    "endTime": "2020-05-20 13:14:00",
                    "duration": 123,
                    "status": 0,
                    "result": "执行成功",
                    "createTime": "2020-05-02 05:20:00",
                }
            ]
        }
    }
