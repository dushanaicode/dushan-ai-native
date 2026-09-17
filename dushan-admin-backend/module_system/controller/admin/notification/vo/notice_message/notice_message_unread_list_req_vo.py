from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class NoticeMessageUnreadListReqVO(BaseRequestVO):
    """管理后台 - 获取未读站内信列表 Request VO"""

    size: Annotated[int, Field(10, description="返回数量", ge=1)]
