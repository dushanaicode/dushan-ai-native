from __future__ import annotations

from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseDTO


class SocialWxJsapiSignatureRespDTO(BaseDTO):
    """微信公众号 JSAPI 签名 Response DTO"""

    app_id: Annotated[str | None, Field(default=None, description="微信公众号的 appId")]
    nonce_str: Annotated[str | None, Field(default=None, description="匿名串")]
    timestamp: Annotated[int | None, Field(default=None, description="时间戳")]
    url: Annotated[str | None, Field(default=None, description="URL")]
    signature: Annotated[str | None, Field(default=None, description="签名")]
