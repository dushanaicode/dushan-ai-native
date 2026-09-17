from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.email import Email


class MailLogPageReqVO(PageQuery):
    """管理后台 - 邮件日志分页列表 Request VO"""

    user_id: Annotated[SnowflakeIdInput | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    account_id: Annotated[SnowflakeIdInput | None, Field(None, description="邮箱账号编号")]
    template_id: Annotated[SnowflakeIdInput | None, Field(None, description="模板编号")]
    template_code: Annotated[str | None, Field(None, description="模板编码")]
    template_nickname: Annotated[str | None, Field(None, description="发送人名称")]
    template_title: Annotated[str | None, Field(None, description="邮件标题")]
    from_mail: Annotated[str | None, Field(None, description="发送邮箱")]
    to_mail: Annotated[str | None, Field(None, description="接收邮箱")]
    account_username: Annotated[str | None, Field(None, description="邮箱账号")]
    send_status: Annotated[int | None, Field(None, description="发送状态")]
    send_time_begin: Annotated[datetime | None, Field(None, description="发送时间开始")]
    send_time_end: Annotated[datetime | None, Field(None, description="发送时间结束")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "accountId": 1024,
                    "templateId": 2048,
                    "templateCode": "test_01",
                    "templateNickname": "渡山源码",
                    "templateTitle": "注册成功",
                    "fromMail": "729227973@qq.com",
                    "toMail": "729227973@qq.com",
                    "accountUsername": "dushan",
                    "sendStatus": 0,
                    "sendTimeBegin": "2022-07-01T10:10:10",
                    "sendTimeEnd": "2022-07-31T23:59:59",
                    "userId": 100,
                    "userType": 1,
                }
            ]
        }
    }

    @field_validator("to_mail", mode="before")
    @classmethod
    def _validate_to_mail(cls, v: Any) -> Any:
        if v is not None:
            Email.require_email(field_name="to_mail", value=v, error_msg="邮箱格式错误")
        return v
