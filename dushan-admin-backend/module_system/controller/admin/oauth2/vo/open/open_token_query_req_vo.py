from framework.common.schemas.base_request_vo import BaseRequestVO


class OAuth2TokenQueryReqVO(BaseRequestVO):
    token: str
