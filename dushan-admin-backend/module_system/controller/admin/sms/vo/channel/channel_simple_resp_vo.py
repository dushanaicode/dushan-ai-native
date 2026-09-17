from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.not_null import NotNull


class SmsChannelSimpleRespVO(BaseVO):
    """管理后台 - 短信渠道精简信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    signature: Annotated[str, Field(..., description="短信签名")]
    code: Annotated[str, Field(..., description="渠道编码，参见 SmsChannelEnum 枚举类")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1024, "signature": "渡山源码", "code": "DUSHAN_YUANMA"}]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="id", value=v, error_msg="编号不能为空")
        return v

    @field_validator("signature", mode="before")
    @classmethod
    def _validate_signature(cls, v: str) -> str:
        NotNull.require_not_null(field_name="signature", value=v, error_msg="短信签名不能为空")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        NotNull.require_not_null(field_name="code", value=v, error_msg="渠道编码不能为空")
        return v
