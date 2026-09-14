from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from framework.starter_security.model.login_session import IdentityId


class WorkloadIdentity(BaseModel):
    """经消息提供者认证的系统工作负载；没有账号、角色或任意租户数据权限。"""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    application_id: IdentityId
    domain: IdentityId
    service_id: IdentityId
    tenant_id: IdentityId | None
    audience: IdentityId
    capabilities: frozenset[Annotated[str, Field(min_length=1, max_length=256)]] = Field(
        max_length=64
    )
    expires_at: AwareDatetime

    def __repr_args__(self):
        return iter(())
