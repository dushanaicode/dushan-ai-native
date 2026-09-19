from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import SnowflakeCursorStr, SnowflakeIdStr
from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty
from framework.starter_excel.public import (
    ExcelColumn,
    JsonConverter,
)


class OperateLogRespVO(BaseVO):
    """管理后台 - 操作日志信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr, Field(None, description="日志编号"), ExcelColumn(title="日志编号")
    ]
    trace_id: Annotated[str, Field(None, description="链路追踪编号")]
    user_id: Annotated[
        SnowflakeCursorStr, Field(None, description="用户编号"), ExcelColumn(title="用户编号")
    ]
    type: Annotated[str, Field(None, description="操作模块类型"), ExcelColumn(title="操作模块类型")]
    sub_type: Annotated[str, Field(None, description="操作名"), ExcelColumn(title="操作名")]
    biz_id: Annotated[
        SnowflakeCursorStr,
        Field(None, description="操作模块业务编号"),
        ExcelColumn(title="操作模块业务编号"),
    ]
    action: Annotated[
        str | None, Field(None, description="操作明细"), ExcelColumn(title="操作明细")
    ]
    extra: Annotated[str | None, Field(None, description="拓展字段")]
    request_method: Annotated[
        str, Field(..., description="请求方法名"), ExcelColumn(title="请求方法名")
    ]
    request_url: Annotated[str, Field(None, description="请求地址"), ExcelColumn(title="请求地址")]
    user_ip: Annotated[str, Field(None, description="用户 IP"), ExcelColumn(title="用户IP")]
    user_agent: Annotated[str, Field(None, description="浏览器 UserAgent")]
    create_time: Annotated[
        datetime, Field(None, description="创建时间"), ExcelColumn(title="创建时间")
    ]
    user_info: Annotated[
        dict[str, Any] | None,
        Field(None, description="用户信息"),
        ExcelColumn(title="用户信息", converter=JsonConverter()),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "traceId": "89aca178-a370-411c-ae02-3f0d672be4ab",
                    "userId": 1024,
                    "type": "订单",
                    "subType": "创建订单",
                    "bizId": 1,
                    "action": "修改编号为 1 的用户信息，将性别从男改成女，将姓名从渡山改成源码。",
                    "extra": "{'orderId': 1}",
                    "requestMethod": "GET",
                    "requestUrl": "/xxx/yyy",
                    "userIp": "127.0.0.1",
                    "userAgent": "Mozilla/5.0",
                    "createTime": "2020-05-20T05:20:00Z",
                    "userInfo": {"username": "admin", "nickname": "管理员"},
                }
            ]
        }
    }

    @field_validator("request_method", mode="before")
    @classmethod
    def _validate_request_method(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(
            field_name="request_method", value=v, error_msg="请求方法名不能为空"
        )
        return v
