from framework.common.schemas import BaseRequestVO


class OAuth2TokenQueryReqVO(BaseRequestVO):
    token: str
