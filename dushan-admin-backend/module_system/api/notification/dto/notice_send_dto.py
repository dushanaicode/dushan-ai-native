from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class NoticeSendDTO(BaseDTO):
    """动态发送通知 DTO"""

    title: Annotated[str, Field(..., description="通知标题")]
    content: Annotated[str, Field(..., description="通知内容")]
    user_ids: Annotated[list[int], Field(..., description="接收用户 ID 列表")]
    notice_code: Annotated[str, Field(..., description="内置通知模板编码")]
    channels: Annotated[list[str] | None, Field(None, description="覆盖模板的通知渠道")]
    publisher_info: Annotated[
        dict[str, Any] | None, Field(None, description="发布者详细信息（LoginUser.info）")
    ]
