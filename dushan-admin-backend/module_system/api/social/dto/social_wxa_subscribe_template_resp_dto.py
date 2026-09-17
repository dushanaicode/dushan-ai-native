from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class SocialWxaSubscribeTemplateRespDTO(BaseDTO):
    """小程序订阅消息模版 Response DTO"""

    id: Annotated[str | None, Field(default=None, description="模版编号")]
    title: Annotated[str | None, Field(default=None, description="模版标题")]
    content: Annotated[str | None, Field(default=None, description="模版内容")]
    example: Annotated[str | None, Field(default=None, description="模板内容示例")]
    type: Annotated[int | None, Field(default=None, description="模版类型")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "template_123",
                    "title": "订阅通知",
                    "content": "您的订单已发货",
                    "example": "您的订单{{orderNo.DATA}}已发货",
                    "type": 1,
                }
            ]
        }
    }
