from pydantic import ConfigDict

from framework.common.schemas import BaseRequestVO


class OAuth2AuthorizeInfoReqVO(BaseRequestVO):
    model_config = ConfigDict(alias_generator=None)
    client_id: str
