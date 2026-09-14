from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProtectionSubject(BaseModel):
    """由受信任的调用方提供身份；本模型不认证身份，也不读取客户端身份头。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["principal", "client_ip", "node", "global", "custom"]
    identifier: str = Field(min_length=1, max_length=1024)
    realm: str | None = None
    tenant_id: str | None = None
    membership_id: str | None = None
