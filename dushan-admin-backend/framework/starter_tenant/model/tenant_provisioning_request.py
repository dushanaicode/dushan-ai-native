from pydantic import BaseModel, ConfigDict, Field


class TenantProvisioningRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)
    idempotency_key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
