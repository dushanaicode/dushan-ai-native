from pydantic import BaseModel, ConfigDict, JsonValue


class InfraSocketPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: JsonValue
