from pydantic import BaseModel, ConfigDict, Field, model_validator

from framework.starter_websocket.definitions.enums.socket_target_kind import SocketTargetKind


class SocketTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: SocketTargetKind
    audience: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    tenant_id: str | None = Field(default=None, min_length=1, max_length=256)
    member_id: str | None = Field(default=None, min_length=1, max_length=256)
    client_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def validate_target(self):
        if self.kind is SocketTargetKind.CLIENT:
            valid = self.client_id is not None and self.member_id is None
        elif self.kind is SocketTargetKind.MEMBER:
            valid = (
                self.tenant_id is not None and self.member_id is not None and self.client_id is None
            )
        elif self.kind is SocketTargetKind.TENANT:
            valid = self.tenant_id is not None and self.member_id is None and self.client_id is None
        else:
            valid = self.tenant_id is None and self.member_id is None and self.client_id is None
        if not valid:
            raise ValueError("WebSocket 投递目标字段不匹配")
        return self
