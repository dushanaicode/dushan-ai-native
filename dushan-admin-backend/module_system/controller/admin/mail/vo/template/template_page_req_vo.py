from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.in_enum import InEnum


class MailTemplatePageReqVO(PageQuery):
    """管理后台 - 邮件模版分页列表 Request VO"""

    status: Annotated[int | None, Field(None, description="状态，参见 StatusEnum 枚举")]
    code: Annotated[str | None, Field(None, description="标识，模糊匹配")]
    name: Annotated[str | None, Field(None, description="名称，模糊匹配")]
    account_id: Annotated[SnowflakeIdInput | None, Field(None, description="账号编号")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]

    @field_validator("status", mode="after")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "test_01",
                    "name": "测试邮件模版",
                    "accountId": 1024,
                    "status": 0,
                    "createTime": ["2022-07-01", "2022-07-01"],
                }
            ]
        }
    }
