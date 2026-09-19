from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.contracts import SnowflakeCursorStr, SnowflakeIdStr
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
    JsonConverter,
)
from module_infra.definitions.enums.logger.api_error_log_process_status_enum import (
    ApiErrorLogProcessStatusEnum,
)
from module_infra.framework.excel.log_user_type_converter import LogUserTypeConverter


class ApiErrorLogRespVO(BaseVO):
    """管理后台 - API 错误日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号"), ExcelColumn(title="编号")]
    trace_id: Annotated[
        str, Field(..., description="链路追踪编号"), ExcelColumn(title="链路追踪编号")
    ]
    user_id: Annotated[
        SnowflakeCursorStr | None,
        Field(None, description="用户编号"),
        ExcelColumn(title="用户编号"),
    ]
    user_type: Annotated[
        int,
        Field(..., description="用户类型"),
        ExcelColumn(title="用户类型", converter=LogUserTypeConverter()),
    ]
    application_name: Annotated[str, Field(..., description="应用名"), ExcelColumn(title="应用名")]
    request_method: Annotated[
        str, Field(..., description="请求方法名"), ExcelColumn(title="请求方法名")
    ]
    request_url: Annotated[str, Field(..., description="请求地址"), ExcelColumn(title="请求地址")]
    request_params: Annotated[
        dict[str, Any] | None,
        Field(None, description="请求参数 (JSON对象)"),
        ExcelColumn(title="请求参数", converter=JsonConverter()),
    ]
    user_ip: Annotated[str, Field(..., description="用户 IP"), ExcelColumn(title="用户 IP")]
    user_agent: Annotated[str, Field(..., description="浏览器 UA"), ExcelColumn(title="浏览器 UA")]
    exception_time: Annotated[
        datetime, Field(..., description="异常发生时间"), ExcelColumn(title="异常发生时间")
    ]
    exception_name: Annotated[str, Field(..., description="异常名"), ExcelColumn(title="异常名")]
    exception_message: Annotated[
        str, Field(..., description="异常导致的消息"), ExcelColumn(title="异常导致的消息")
    ]
    exception_root_cause_message: Annotated[
        str, Field(..., description="异常导致的根消息"), ExcelColumn(title="异常导致的根消息")
    ]
    exception_stack_trace: Annotated[
        str, Field(..., description="异常的栈轨迹"), ExcelColumn(title="异常的栈轨迹")
    ]
    exception_class_name: Annotated[
        str, Field(..., description="异常发生的类全名"), ExcelColumn(title="异常发生的类全名")
    ]
    exception_file_name: Annotated[
        str, Field(..., description="异常发生的类文件"), ExcelColumn(title="异常发生的类文件")
    ]
    exception_method_name: Annotated[
        str, Field(..., description="异常发生的方法名"), ExcelColumn(title="异常发生的方法名")
    ]
    exception_line_number: Annotated[
        int,
        Field(..., description="异常发生的方法所在行"),
        ExcelColumn(title="异常发生的方法所在行"),
    ]
    process_status: Annotated[
        int,
        Field(..., description="处理状态"),
        ExcelColumn(title="处理状态", converter=EnumConverter(ApiErrorLogProcessStatusEnum)),
    ]
    process_time: Annotated[
        datetime | None, Field(None, description="处理时间"), ExcelColumn(title="处理时间")
    ]
    process_user_id: Annotated[
        SnowflakeIdStr | None,
        Field(None, description="处理用户编号"),
        ExcelColumn(title="处理用户编号"),
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "trace_id": "66600cb6-7852-11eb-9439-0242ac130002",
                    "userId": 1024,
                    "userType": 1,
                    "applicationName": "dashboard",
                    "requestMethod": "GET",
                    "requestUrl": "/xx/yy",
                    "requestParams": {"key": "value"},
                    "userIp": "127.0.0.1",
                    "userAgent": "Mozilla/5.0",
                    "exceptionTime": "2020-05-20T05:20:00Z",
                    "exceptionName": "NullPointerException",
                    "exceptionMessage": "空指针异常",
                    "exceptionRootCauseMessage": "对象为空",
                    "exceptionStackTrace": "at com.example.Class.method(Class.python:123)",
                    "exceptionClassName": "com.example.Class",
                    "exceptionFileName": "Class.python",
                    "exceptionMethodName": "method",
                    "exceptionLineNumber": 123,
                    "processStatus": 0,
                    "processTime": "2020-05-20T05:20:00Z",
                    "processUserId": 233,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
