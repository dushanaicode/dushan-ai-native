from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.enums.status_enum import StatusEnum
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.in_enum import InEnum
from module_system.definitions.enums.notification.notice_type_enum import NoticeTypeEnum


class NoticePageReqVO(PageQuery):
    """管理后台 - 系统通知分页列表 Request VO"""

    title: Annotated[str | None, Field(None, description="通知标题，模糊匹配")]
    type: Annotated[int | None, Field(None, description="通知类型，参见 NoticeTypeEnum 枚举类")]
    user_type: Annotated[int | None, Field(None, description="用户类型，参见 UserTypeEnum 枚举类")]
    status: Annotated[int | None, Field(None, description="通知状态，参见 StatusEnum 枚举类")]
    publisher: Annotated[str | None, Field(None, description="发布人，模糊匹配")]
    channels: Annotated[list[str] | None, Field(None, description="推送渠道编码数组")]
    create_time: Annotated[list | None, Field(None, exclude=True, description="创建时间范围")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "系统升级",
                    "type": 1,
                    "userType": 1,
                    "status": 0,
                    "publisher": "渡山源码",
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }

    @field_validator("status", mode="after")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="status",
                value=v,
                enum_class=StatusEnum,
                error_msg="通知状态必须在指定范围",
            )
        return v

    @field_validator("type", mode="after")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="type",
                value=v,
                enum_class=NoticeTypeEnum,
                error_msg="通知类型必须在指定范围",
            )
        return v

    @field_validator("user_type", mode="after")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="user_type",
                value=v,
                enum_class=UserTypeEnum,
                error_msg="用户类型必须在指定范围",
            )
        return v

    @field_validator("channels", mode="after")
    @classmethod
    def _validate_channels(cls, v: list[str] | None) -> list[str] | None:
        from module_system.definitions.enums.notification.notification_channel_enum import (
            NotificationChannelEnum,
        )

        if v is None:
            return v
        for ch in v:
            InEnum.require_in_enum(
                field_name="channels",
                value=ch,
                enum_class=NotificationChannelEnum,
                error_msg="推送渠道不在允许范围",
            )
        return v
