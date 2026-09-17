from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.email import Email
from framework.common.validator.not_null import NotNull


class MailAccountSimpleRespVO(BaseVO):
    """管理后台 - 邮箱账号精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="邮箱编号")]
    mail: Annotated[str, Field(..., description="邮箱")]
    model_config = {"json_schema_extra": {"examples": [{"id": 1024, "mail": "729227973@qq.com"}]}}

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="邮箱编号不能为空")
        return v

    @field_validator("mail", mode="before")
    @classmethod
    def _validate_mail(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="mail", value=v, error_msg="邮箱不能为空")
        Email.require_email(field_name="mail", value=v, error_msg="邮箱格式错误")
        return v
