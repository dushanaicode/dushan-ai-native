from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class NoticeMessageMarkReadReqDTO(BaseDTO):
    """站内信已读请求。"""

    user_id: Annotated[int, Field(..., description="用户编号")]
    user_type: Annotated[int, Field(..., description="用户类型")]
    notice_message_id: Annotated[int, Field(..., description="站内信消息编号")]
