from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ClientMessage(BaseModel):
    """客户端唯一文本信封；标识只作关联，不作为身份凭据。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
        validate_by_name=True,
        serialize_by_alias=True,
        hide_input_in_errors=True,
    )
    type: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", max_length=128)
    payload: JsonValue = None
    request_id: str | None = Field(
        default=None, alias="requestId", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
    )
    sender_id: str | None = Field(
        default=None, alias="senderId", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
    )
    timestamp: float | None = Field(default=None, ge=0)
