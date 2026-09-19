from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotEmpty, NotNull


class MailTemplateSaveReqVO(BaseRequestVO):
    """管理后台 - 邮件模版创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="编号")]
    name: Annotated[str, Field(..., description="模版名称")]
    code: Annotated[str, Field(..., description="模版编码")]
    account_id: Annotated[SnowflakeIdInput, Field(..., description="发送的邮箱账号编号")]
    nickname: Annotated[str, Field(..., description="发件人名称")]
    title: Annotated[str, Field(..., description="邮件标题")]
    content: Annotated[str, Field(..., description="邮件内容")]
    params: Annotated[list[str] | None, Field(None, description="参数数组")]
    status: Annotated[int, Field(..., description="开启状态")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "测试邮件模版",
                    "code": "test_01",
                    "accountId": 2048,
                    "nickname": "渡山源码",
                    "title": "注册成功",
                    "content": "你好，{name}。你注册成功啦",
                    "params": ["name", "code"],
                    "status": 0,
                    "remark": "备注",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="名称不能为空")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="code", value=v, error_msg="模版编号不能为空")
        return v

    @field_validator("account_id", mode="before")
    @classmethod
    def _validate_account_id(cls, v: Any) -> Any:
        NotNull.require_not_null(
            field_name="account_id", value=v, error_msg="发送的邮箱账号编号不能为空"
        )
        return v

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="title", value=v, error_msg="标题不能为空")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def _validate_content(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="content", value=v, error_msg="内容不能为空")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status",
            value=v,
            enum_class=StatusEnum,
            error_msg="状态必须在指定范围 {values}",
        )
        return v
