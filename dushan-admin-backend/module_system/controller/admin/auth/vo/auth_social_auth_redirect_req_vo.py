from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class AuthSocialAuthRedirectReqVO(BaseRequestVO):
    """管理后台 - 社交授权跳转 Request VO"""

    type: Annotated[int, Field(..., description="社交平台的类型")]
    redirect_uri: Annotated[str, Field(..., description="重定向URI")]
