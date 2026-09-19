from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotNull
from module_system.controller.admin.notification.vo.notice_log.notice_log_notice_publisher_info_vo import (
    NoticePublisherInfoVO,
)


class NoticeLogRespVO(BaseVO):
    """管理后台 - 推送日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="推送日志ID")]
    notice_id: Annotated[SnowflakeIdStr, Field(..., description="关联的通知编号")]
    notice_title: Annotated[str, Field(..., description="通知标题")]
    notice_type: Annotated[int, Field(..., description="通知类型")]
    push_target_type: Annotated[
        int, Field(..., description="推送目标类型: 1=按用户, 2=按部门, 3=混合")
    ]
    target_user_ids: Annotated[
        list[SnowflakeIdStr] | None, Field(None, description="目标用户ID列表")
    ]
    target_dept_ids: Annotated[
        list[SnowflakeIdStr] | None, Field(None, description="目标部门ID列表")
    ]
    target_dept_names: Annotated[list[str] | None, Field(None, description="目标部门名称列表")]
    push_channels: Annotated[list[str], Field(..., description="推送渠道")]
    total_count: Annotated[int, Field(..., description="推送总人数")]
    success_count: Annotated[int, Field(..., description="成功数")]
    fail_count: Annotated[int, Field(..., description="失败数")]
    push_status: Annotated[int, Field(..., description="推送状态")]
    publisher_info: Annotated[NoticePublisherInfoVO | None, Field(None, description="发布者信息")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="ID 不能为空")
        return v

    @field_validator("notice_id", mode="before")
    @classmethod
    def _validate_notice_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="notice_id", value=v, error_msg="通知编号不能为空")
        return v
