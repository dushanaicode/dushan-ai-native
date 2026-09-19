from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class SocialUserRespDTO(BaseDTO):
    """社交用户 Response DTO"""

    openid: Annotated[str | None, Field(default=None, description="社交用户的 openid")]
    nickname: Annotated[str | None, Field(default=None, description="社交用户的昵称")]
    avatar: Annotated[str | None, Field(default=None, description="社交用户的头像")]
    user_id: Annotated[int | None, Field(default=None, description="关联的用户编号")]
