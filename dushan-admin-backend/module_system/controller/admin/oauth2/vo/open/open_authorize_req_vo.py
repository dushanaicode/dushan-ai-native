from pydantic import ConfigDict

from framework.common.schemas import BaseRequestVO


class OAuth2AuthorizeReqVO(BaseRequestVO):
    """OAuth2 授权参数按协议保留 snake_case 字段名。"""

    model_config = ConfigDict(alias_generator=None)
    redirect_uri: str
    auto_approve: bool
    response_type: str
    client_id: str
    scope: str | None = None
    state: str | None = None
