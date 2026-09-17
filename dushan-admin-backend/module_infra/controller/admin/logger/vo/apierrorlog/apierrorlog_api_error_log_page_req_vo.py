from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeReferenceInput,
)
from framework.common.page.schemas.page_query import PageQuery


class ApiErrorLogPageReqVO(PageQuery):
    """管理后台 - API 错误日志分页列表 Request VO"""

    user_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    application_name: Annotated[str | None, Field(None, description="应用名")]
    request_url: Annotated[str | None, Field(None, description="请求地址")]
    exception_time: Annotated[
        list[datetime] | None,
        Field(None, exclude=True, description="异常发生时间范围 [开始, 结束]"),
    ]
    process_status: Annotated[int | None, Field(None, description="处理状态")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1024,
                    "userType": 1,
                    "applicationName": "dashboard",
                    "requestUrl": "/xx/yy",
                    "exceptionTime": ["2020-05-02 05:20:00", "2020-05-02 13:14:00"],
                    "processStatus": 0,
                }
            ]
        }
    }

    @field_validator("user_id", "user_type", "process_status", mode="before")
    @classmethod
    def _validate_integer_empty_str(cls, v: Any) -> int | None:
        if isinstance(v, str) and v == "":
            return None
        return v
