from pydantic import BaseModel, ConfigDict, Field


class RequestIdentity(BaseModel):
    """安全提供者完成认证及当前路由授权后交付的身份，不从客户端身份头构造。"""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    principal_id: str = Field(min_length=1, max_length=256)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=256)
