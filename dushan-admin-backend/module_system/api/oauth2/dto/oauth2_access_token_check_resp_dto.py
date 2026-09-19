from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class OAuth2AccessTokenCheckRespDTO(BaseDTO):
    """OAuth2.0 访问令牌的校验 Response DTO"""

    user_id: Annotated[int | None, Field(description="用户编号")]
    user_type: Annotated[int | None, Field(description="用户类型")]
    user_info: Annotated[dict[str, object] | None, Field(description="用户信息")]
    tenant_id: Annotated[str | None, Field(description="租户编号")]
    scopes: Annotated[list[str] | None, Field(description="授权范围的数组")]
    expires_time: Annotated[datetime | None, Field(description="过期时间")]
