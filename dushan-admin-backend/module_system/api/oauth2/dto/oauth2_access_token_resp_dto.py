from __future__ import annotations

from datetime import datetime

from framework.common.schemas.base_dto import BaseDTO


class OAuth2AccessTokenRespDTO(BaseDTO):
    """令牌签发结果，只在创建或轮换时交付明文。"""

    access_token: str
    refresh_token: str | None
    user_id: int
    user_type: int
    tenant_id: str
    client_id: str
    scopes: list[str]
    expires_time: datetime
    refresh_expires_time: datetime | None
