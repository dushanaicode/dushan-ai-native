from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeReferenceInput,
)
from framework.common.page import PageQuery


class ApiAccessLogPageReqVO(PageQuery):
    """管理后台 - API 访问日志分页列表 Request VO"""

    user_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    application_name: Annotated[str | None, Field(None, description="应用名")]
    request_url: Annotated[str | None, Field(None, description="请求地址，模糊匹配")]
    begin_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="请求时间范围")
    ]
    duration: Annotated[int | None, Field(None, description="执行时长,大于等于，单位：毫秒")]
    result_code: Annotated[int | None, Field(None, description="结果码")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1024,
                    "userType": 2,
                    "applicationName": "dashboard",
                    "requestUrl": "/xxx/yyy",
                    "beginTime": ["2020-05-02 05:20:00", "2020-05-02 13:14:00"],
                    "duration": 100,
                    "resultCode": 0,
                }
            ]
        }
    }

    @field_validator("user_id", "user_type", "duration", "result_code", mode="before")
    @classmethod
    def _validate_integer_empty_str(cls, v: Any) -> int | None:
        if isinstance(v, str) and v == "":
            return None
        return v
