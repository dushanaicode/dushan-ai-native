from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageEnvelope(BaseModel):
    """JSON 传输信封，关键字段及扩展追踪头全部由 HMAC 覆盖。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1]
    message_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    destination: str = Field(min_length=1, max_length=128)
    authority: Literal["session", "workload"]
    capability: str | None
    tenant_id: str | None
    proof: str = Field(min_length=1, max_length=87384)
    payload: str
    issued_at: float = Field(allow_inf_nan=False)
    expires_at: float = Field(allow_inf_nan=False)
    attempt: int = Field(strict=True, ge=0, le=32)
    ready_at: float = Field(allow_inf_nan=False)
    consumer_key: str | None
    trace_headers: dict[str, str]
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")
