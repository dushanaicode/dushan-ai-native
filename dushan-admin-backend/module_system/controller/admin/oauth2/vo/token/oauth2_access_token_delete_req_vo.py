from framework.common.contracts import SnowflakeIdInput
from framework.common.schemas import BaseRequestVO


class OAuth2AccessTokenDeleteReqVO(BaseRequestVO):
    id: SnowflakeIdInput
