from typing import Literal

from framework.common.schemas import BaseVO


class AuthSocialProviderRespVO(BaseVO):
    type: int
    name: str
    source: str
    mode: Literal["browser", "native"]
    code_parameter: str
