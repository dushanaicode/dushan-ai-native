from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_null import NotNull
from module_system.controller.admin.notification.vo.notice_log.notice_log_notice_publisher_info_vo import (
    NoticePublisherInfoVO,
)


class NoticeMessageRespVO(BaseVO):
    """管理后台 - 站内信信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="ID")]
    user_id: Annotated[SnowflakeIdStr, Field(..., description="用户编号")]
    user_type: Annotated[int, Field(..., description="用户类型，参见 UserTypeEnum 枚举")]
    notice_id: Annotated[SnowflakeIdStr, Field(..., description="关联的通知编号")]
    notice_content: Annotated[str | None, Field(None, description="通知内容")]
    publisher_info: Annotated[NoticePublisherInfoVO | None, Field(None, description="发布者信息")]
    notice_title: Annotated[str, Field(..., description="通知标题")]
    notice_type: Annotated[int, Field(..., description="通知类型")]
    read_status: Annotated[bool, Field(..., description="是否已读")]
    read_time: Annotated[datetime | None, Field(None, description="阅读时间")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "userId": 1024,
                    "userType": 1,
                    "noticeId": 1,
                    "noticeContent": "系统升级通知",
                    "publisherInfo": {
                        "username": "dushan",
                        "nickname": "渡山",
                        "avatar": "https://example.com/avatar.jpg",
                    },
                    "noticeTitle": "系统升级通知",
                    "noticeType": 1,
                    "readStatus": True,
                    "readTime": "2020-05-20 05:20:00",
                    "createTime": "2020-05-20 05:20:00",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="ID 不能为空")
        return v

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_id", value=v, error_msg="用户编号不能为空")
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

    @field_validator("notice_id", mode="before")
    @classmethod
    def _validate_notice_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="notice_id", value=v, error_msg="通知编号不能为空")
        return v

    @field_validator("notice_title", mode="before")
    @classmethod
    def _validate_notice_title(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="notice_title", value=v, error_msg="通知标题不能为空")
        return v

    @field_validator("notice_type", mode="before")
    @classmethod
    def _validate_notice_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="notice_type", value=v, error_msg="通知类型不能为空")
        return v

    @field_validator("read_status", mode="before")
    @classmethod
    def _validate_read_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="read_status", value=v, error_msg="是否已读不能为空")
        return v

    @field_validator("create_time", mode="before")
    @classmethod
    def _validate_create_time(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="create_time", value=v, error_msg="创建时间不能为空")
        return v
