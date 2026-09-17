from pydantic import ConfigDict

from framework.common.schemas.base_request_vo import BaseRequestVO


class OAuth2AuthorizeInfoReqVO(BaseRequestVO):
    model_config = ConfigDict(alias_generator=None)
    client_id: str
