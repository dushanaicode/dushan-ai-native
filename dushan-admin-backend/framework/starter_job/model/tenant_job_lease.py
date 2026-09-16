from pydantic import AwareDatetime, BaseModel, ConfigDict


class TenantJobLease(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)
    request_id: str
    tenant_id: str
    token: str
    expires_at: AwareDatetime
