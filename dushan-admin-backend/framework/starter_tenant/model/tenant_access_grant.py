from pydantic import AwareDatetime, BaseModel, ConfigDict

from framework.starter_security.model.login_session import IdentityId
from framework.starter_tenant.model.tenant_resource_grant import TenantResourceGrant


class TenantAccessGrant(BaseModel):
    """由业务权威提供者返回的目标、资源、动作与有效期；空权限不允许 SQL。"""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", hide_input_in_errors=True)
    tenant_id: IdentityId
    source: IdentityId
    resources: tuple[TenantResourceGrant, ...]
    expires_at: AwareDatetime
    allow_unavailable: bool = False
