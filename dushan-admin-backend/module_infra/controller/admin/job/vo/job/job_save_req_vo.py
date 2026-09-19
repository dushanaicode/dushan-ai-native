from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotEmpty, NotNull


class JobSaveReqVO(BaseRequestVO):
    """管理后台 - 定时任务创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(default=None, description="任务编号")]
    name: Annotated[str, Field(..., description="任务名称")]
    handler_name: Annotated[str, Field(..., description="处理器的名字")]
    handler_param: Annotated[str | None, Field(default=None, description="处理器的参数")]
    cron_expression: Annotated[str, Field(..., description="CRON 表达式")]
    retry_count: Annotated[int, Field(..., description="重试次数")]
    retry_interval: Annotated[int, Field(..., description="重试间隔")]
    monitor_timeout: Annotated[int | None, Field(default=None, description="监控超时时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "测试任务",
                    "handlerName": "sysUserSessionTimeoutJob",
                    "handlerParam": "dushan_job",
                    "cronExpression": "0/10 * * * * *",
                    "retryCount": 3,
                    "retryInterval": 1000,
                    "monitorTimeout": 1000,
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="任务名称不能为空")
        return v

    @field_validator("handler_name", mode="before")
    @classmethod
    def _validate_handler_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(
            field_name="handler_name", value=v, error_msg="处理器的名字不能为空"
        )
        return v

    @field_validator("cron_expression", mode="before")
    @classmethod
    def _validate_cron_expression(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(
            field_name="cron_expression", value=v, error_msg="CRON 表达式不能为空"
        )
        return v

    @field_validator("retry_count", mode="before")
    @classmethod
    def _validate_retry_count(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="retry_count", value=v, error_msg="重试次数不能为空")
        return v

    @field_validator("retry_interval", mode="before")
    @classmethod
    def _validate_retry_interval(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="retry_interval", value=v, error_msg="重试间隔不能为空")
        return v
