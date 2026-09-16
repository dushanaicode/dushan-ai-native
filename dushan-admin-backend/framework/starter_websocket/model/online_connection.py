from pydantic import BaseModel, ConfigDict, Field


class OnlineConnection(BaseModel):
    """在线查询端口的非凭证信息；不发布 Token digest 或完整会话。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    client_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    instance: str = Field(pattern=r"^[a-f0-9]{32}$")
    audience: str
    tenant_id: str | None
    member_id: str | None
