from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.enums import StatusEnum, UserTypeEnum
from framework.common.schemas import BaseRequestVO
from framework.common.validator import InEnum, NotEmpty, NotNull, Size
from module_system.definitions.enums.notification.notice_type_enum import NoticeTypeEnum
from module_system.definitions.enums.notification.notification_channel_enum import (
    NotificationChannelEnum,
)


class NoticeSaveReqVO(BaseRequestVO):
    """管理后台 - 系统通知创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="通知编号")]
    title: Annotated[str, Field(..., description="通知标题")]
    type: Annotated[int, Field(..., description="通知类型，参见 NoticeTypeEnum 枚举类")]
    user_type: Annotated[int, Field(..., description="用户类型，参见 UserTypeEnum 枚举类")]
    channels: Annotated[
        list[str], Field(..., description="通知渠道,参见 NotificationChannelEnum 枚举类")
    ]
    sms_template_code: Annotated[
        str | None, Field(None, description="短信模板编码,选择SMS渠道时必填")
    ]
    mail_account_id: Annotated[
        SnowflakeIdInput | None, Field(None, description="邮箱账号编号,选择MAIL渠道时必填")
    ]
    content: Annotated[str, Field(..., description="通知内容")]
    publisher: Annotated[str | None, Field(None, description="发布人")]
    status: Annotated[int, Field(..., description="通知状态，参见 StatusEnum 枚举类")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "title": "系统升级通知",
                    "type": 1,
                    "userType": 1,
                    "channels": ["INTERNAL", "MAIL"],
                    "content": "系统将于今晚22:00-23:00进行升级维护",
                    "status": 0,
                    "publisher": "渡山源码",
                }
            ]
        }
    }

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="title", value=v, error_msg="通知标题不能为空")
        Size.require_size(
            field_name="title",
            value=v,
            min_length=0,
            max_length=50,
            error_msg="通知标题不能超过50个字符",
        )
        return v

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type", value=v, error_msg="通知类型不能为空")
        InEnum.require_in_enum(
            field_name="type",
            value=v,
            enum_class=NoticeTypeEnum,
            error_msg="通知类型必须在指定范围",
        )
        return v

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_type", value=v, error_msg="用户类型不能为空")
        InEnum.require_in_enum(
            field_name="user_type",
            value=v,
            enum_class=UserTypeEnum,
            error_msg="用户类型必须在指定范围",
        )
        return v

    @field_validator("channels", mode="before")
    @classmethod
    def _validate_channels(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="channels", value=v, error_msg="通知渠道不能为空")
        if isinstance(v, list):
            for channel in v:
                InEnum.require_in_enum(
                    field_name="channel",
                    value=channel,
                    enum_class=NotificationChannelEnum,
                    error_msg="通知渠道必须在指定范围",
                )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="通知状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="通知状态必须在指定范围"
        )
        return v
