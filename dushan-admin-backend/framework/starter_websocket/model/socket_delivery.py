from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from framework.starter_websocket.model.socket_message import SocketMessage
from framework.starter_websocket.model.socket_target import SocketTarget


class SocketDelivery(BaseModel):
    """跨进程传输信封，HMAC 覆盖全部字段，id 仅标识本次发布。

    只验证真实性与有效期，不保证有效期内去重；需要持久投递语义时使用 MQ。
    """

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
