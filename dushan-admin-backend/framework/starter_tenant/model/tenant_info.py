from pydantic import BaseModel, ConfigDict

from framework.starter_security.model.login_session import IdentityId


class TenantInfo(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)
    tenant_id: IdentityId
    enabled: bool
