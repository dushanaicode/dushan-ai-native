from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotNull


class MailTemplateSimpleRespVO(BaseVO):
    """管理后台 - 邮件模版精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    name: Annotated[str, Field(..., description="模版名称")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "name": "测试邮件模版"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="模版编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="模版名字不能为空")
        return v
