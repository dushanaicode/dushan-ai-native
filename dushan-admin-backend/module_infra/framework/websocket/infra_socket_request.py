from pydantic import BaseModel, ConfigDict


class InfraSocketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
