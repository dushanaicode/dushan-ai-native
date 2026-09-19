from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.contracts import SnowflakeCursorStr, SnowflakeIdStr
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    DictConverter,
    ExcelColumn,
    JsonConverter,
)
from module_infra.definitions.constants.dict_type_constants import (
    DictTypeConstants as InfraDictTypeConstants,
)
from module_infra.framework.excel.log_user_type_converter import LogUserTypeConverter


class ApiAccessLogRespVO(BaseVO):
    """管理后台 - API 访问日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="日志主键"), ExcelColumn(title="日志主键")]
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
        Field(..., description="用户类型，参见 UserTypeEnum 枚举"),
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
    response_body: Annotated[
        Any | None,
        Field(None, description="响应结果 (JSON对象/数组/值)"),
        ExcelColumn(title="响应结果", converter=JsonConverter()),
    ]
    user_ip: Annotated[str, Field(..., description="用户 IP"), ExcelColumn(title="用户 IP")]
    user_agent: Annotated[str, Field(..., description="浏览器 UA"), ExcelColumn(title="浏览器 UA")]
    operate_module: Annotated[
        str, Field(..., description="操作模块"), ExcelColumn(title="操作模块")
    ]
    operate_name: Annotated[str, Field(..., description="操作名"), ExcelColumn(title="操作名")]
    operate_type: Annotated[
        int,
        Field(..., description="操作分类"),
        ExcelColumn(title="操作分类", converter=DictConverter(InfraDictTypeConstants.OPERATE_TYPE)),
    ]
    begin_time: Annotated[
        datetime, Field(..., description="开始请求时间"), ExcelColumn(title="开始请求时间")
    ]
    end_time: Annotated[
        datetime, Field(..., description="结束请求时间"), ExcelColumn(title="结束请求时间")
    ]
    duration: Annotated[int, Field(..., description="执行时长"), ExcelColumn(title="执行时长")]
    result_code: Annotated[int, Field(..., description="结果码"), ExcelColumn(title="结果码")]
    result_msg: Annotated[
        str | None, Field(None, description="结果提示"), ExcelColumn(title="结果提示")
    ]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "traceId": "66600cb6-7852-11eb-9439-0242ac130002",
                    "userId": 1024,
                    "userType": 2,
                    "applicationName": "dashboard",
                    "requestMethod": "GET",
                    "requestUrl": "/xxx/yyy",
                    "requestParams": {"key": "value"},
                    "responseBody": {"code": 0, "data": {}},
                    "userIp": "127.0.0.1",
                    "userAgent": "Mozilla/5.0",
                    "operateModule": "商品模块",
                    "operateName": "创建商品",
                    "operateType": 1,
                    "beginTime": "2020-05-20T05:20:00Z",
                    "endTime": "2020-05-02T013:14:00Z",
                    "duration": 100,
                    "resultCode": 0,
                    "resultMsg": "渡山",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
