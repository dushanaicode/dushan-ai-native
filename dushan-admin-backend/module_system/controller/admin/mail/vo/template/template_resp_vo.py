from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.converter.json_converter import JsonConverter
from framework.starter_excel.model.excel_column import ExcelColumn


class MailTemplateRespVO(BaseVO):
    """管理后台 - 邮件模版信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号"), ExcelColumn(title="编号")]
    name: Annotated[str, Field(..., description="模版名称"), ExcelColumn(title="模板名称")]
    code: Annotated[str, Field(..., description="模版编码"), ExcelColumn(title="模板编码")]
    account_id: Annotated[
        SnowflakeIdStr,
        Field(..., description="发送的邮箱账号编号"),
        ExcelColumn(title="邮箱账号编号"),
    ]
    nickname: Annotated[str, Field(..., description="发件人名称"), ExcelColumn(title="发件人名称")]
    title: Annotated[str, Field(..., description="邮件标题"), ExcelColumn(title="邮件标题")]
    content: Annotated[str, Field(..., description="邮件内容"), ExcelColumn(title="邮件内容")]
    params: Annotated[
        list[str] | None,
        Field(None, description="参数数组"),
        ExcelColumn(title="参数数组", converter=JsonConverter()),
    ]
    status: Annotated[
        int,
        Field(..., description="开启状态"),
        ExcelColumn(title="开启状态", converter=EnumConverter(StatusEnum)),
    ]
    remark: Annotated[str | None, Field(None, description="备注"), ExcelColumn(title="备注")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
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
                    "status": 0,
                    "remark": "备注",
                    "createTime": "2022-07-01T10:10:10",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="编号不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="模版名称不能为空")
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="code", value=v, error_msg="模版编号不能为空")
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
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围"
        )
        return v
