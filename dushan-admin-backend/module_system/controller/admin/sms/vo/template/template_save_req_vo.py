from typing import Annotated

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotNull


class SmsTemplateSaveReqVO(BaseRequestVO):
    """管理后台 - 短信模板创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    type: Annotated[int, Field(..., description="短信类型，参见 SmsTemplateTypeEnum 枚举类")]
    status: Annotated[int, Field(..., description="开启状态，参见 StatusEnum 枚举类")]
    code: Annotated[str, Field(..., description="模板编码")]
    name: Annotated[str, Field(..., description="模板名称")]
    content: Annotated[str, Field(..., description="模板内容")]
    remark: Annotated[str | None, Field(None, description="备注")]
    api_template_id: Annotated[str, Field(..., description="短信 API 的模板编号")]
    channel_id: Annotated[SnowflakeIdInput, Field(..., description="短信渠道编号")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "type": 1,
                    "status": 1,
                    "code": "test_01",
                    "name": "dushan",
                    "content": "你好，{name}。你长的太{like}啦！",
                    "remark": "哈哈哈",
                    "apiTemplateId": "4383920",
                    "channelId": 10,
                }
            ]
        }
    }

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: int) -> int:
        NotNull.require_not_null(field_name="type", value=v, error_msg="短信类型不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: int) -> int:
        NotNull.require_not_null(field_name="status", value=v, error_msg="开启状态不能为空")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        NotNull.require_not_null(field_name="code", value=v, error_msg="模板编码不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        NotNull.require_not_null(field_name="name", value=v, error_msg="模板名称不能为空")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def _validate_content(cls, v: str) -> str:
        NotNull.require_not_null(field_name="content", value=v, error_msg="模板内容不能为空")
        return v

    @field_validator("api_template_id", mode="before")
    @classmethod
    def _validate_api_template_id(cls, v: str) -> str:
        NotNull.require_not_null(
            field_name="api_template_id", value=v, error_msg="短信 API 的模板编号不能为空"
        )
        return v

    @field_validator("channel_id", mode="before")
    @classmethod
    def _validate_channel_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="channel_id", value=v, error_msg="短信渠道编号不能为空")
        return v
