from pydantic import BaseModel, ConfigDict, Field

from framework.starter_auth.model.auth_tokens import AuthTokens
from framework.starter_auth.model.external_identity import ExternalIdentity


class AuthResult(BaseModel):
    """外部授权结果，不代表本站登录成功或账号绑定完成。"""

    model_config = ConfigDict(frozen=True)
    identity: ExternalIdentity
    tokens: AuthTokens = Field(repr=False, exclude=True)
