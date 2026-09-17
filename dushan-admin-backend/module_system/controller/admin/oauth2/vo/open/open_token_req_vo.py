from pydantic import ConfigDict

from framework.common.schemas.base_request_vo import BaseRequestVO


class OAuth2TokenReqVO(BaseRequestVO):
    """OAuth2 Token 请求参数（application/x-www-form-urlencoded）"""

    grant_type: str
    code: str | None = None
    redirect_uri: str | None = None
    state: str | None = None
    username: str | None = None
    password: str | None = None
    scope: str | None = None
    refresh_token: str | None = None
    code_verifier: str | None = None
    model_config = ConfigDict(alias_generator=None)
