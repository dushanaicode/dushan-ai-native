from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.page import PageQuery


class NoticeLogPageReqVO(PageQuery):
    """管理后台 - 推送日志分页列表 Request VO"""

    notice_id: Annotated[SnowflakeIdInput | None, Field(None, description="关联通知ID")]
    notice_title: Annotated[str | None, Field(None, description="通知标题")]
    notice_type: Annotated[int | None, Field(None, description="通知类型")]
    push_target_type: Annotated[
        int | None, Field(None, description="推送目标类型: 1=按用户, 2=按部门, 3=混合")
    ]
    push_status: Annotated[
        int | None,
        Field(None, description="推送状态: 0=推送中, 1=全部成功, 2=部分失败, 3=全部失败"),
    ]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
