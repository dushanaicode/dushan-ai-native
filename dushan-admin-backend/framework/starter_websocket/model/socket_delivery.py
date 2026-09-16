from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from framework.starter_websocket.model.socket_message import SocketMessage
from framework.starter_websocket.model.socket_target import SocketTarget


class SocketDelivery(BaseModel):
    """跨进程传输信封，HMAC 覆盖来源、版本、目标、消息与有效期。"""

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    version: Literal[1]
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    instance: str = Field(pattern=r"^[a-f0-9]{32}$")
    action: Literal["deliver", "invalidate"]
    target: SocketTarget | None
    message: SocketMessage | None
    family_id: str | None
    tenant_id: str | None
    issued_at: float = Field(allow_inf_nan=False)
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")
