from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class SocialWxPhoneNumberInfoRespDTO(BaseDTO):
    """微信小程序的手机信息 Response DTO"""

    phone_number: Annotated[
        str | None, Field(default=None, description="用户绑定的手机号（国外手机号会有区号）")
    ]
    pure_phone_number: Annotated[str | None, Field(default=None, description="没有区号的手机号")]
    country_code: Annotated[str | None, Field(default=None, description="区号")]
