from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from framework.starter_security.definitions.enums.security_realm import SecurityRealm
from framework.starter_security.definitions.enums.tenant_access_mode import TenantAccessMode

type IdentityId = Annotated[str, Field(strict=True, min_length=1, max_length=256)]


class LoginSession(BaseModel):
    """业务提供者从当前权威数据构建的会话，尚须由 Security 校验后才可绑定。

    resolve 每次必须读取撤销、会话族、账号启用及凭据版本；不能只返回旧缓存。
    authorization_revision 必须涵盖此身份的权限、角色及授权关系版本。
    不保存明文 token、密码、Cookie、外部 access_token 或完整用户资料。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    application_id: IdentityId
    domain: IdentityId
    token_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_id: IdentityId
    family_id: IdentityId
    # Database BaseDO 的 creator/updater 契约为 String(64)，这里拒绝而不截断。
    account_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    realm: SecurityRealm
    expires_at: AwareDatetime
    revoked: bool
    account_enabled: bool
    credential_revision: int = Field(ge=1)
    current_credential_revision: int = Field(ge=1)
    authorization_revision: IdentityId
    scopes: frozenset[str]
    tenant_id: IdentityId | None = None
    membership_id: IdentityId | None = None
    authority_tenant_id: IdentityId | None = None
    authority_membership_id: IdentityId | None = None
    platform_operator_id: IdentityId | None = None
    support_session_id: IdentityId | None = None
    dept_id: IdentityId | None = None
    access_mode: TenantAccessMode | None = None
    group_id: IdentityId | None = None
    management_relation_id: IdentityId | None = None
    effective_capabilities: frozenset[IdentityId] = frozenset()
    approved_resource: IdentityId | None = None
    approved_action: Literal["read"] | None = None

    @model_validator(mode="after")
    def validate_authority(self):
        tenant = self.realm in {SecurityRealm.TENANT, SecurityRealm.SUPPORT}
        if tenant != (self.tenant_id is not None):
            raise ValueError("租户和支持主体必须绑定租户，账号和平台主体不能携带租户")
        if self.realm is not SecurityRealm.TENANT and any(
            value is not None
            for value in (
                self.membership_id,
                self.authority_tenant_id,
                self.authority_membership_id,
                self.dept_id,
                self.access_mode,
                self.group_id,
                self.management_relation_id,
            )
        ):
            raise ValueError("成员权限只属于 tenant 主体")
        if self.realm is SecurityRealm.TENANT:
            if self.access_mode is TenantAccessMode.DIRECT_MEMBERSHIP:
                if (
                    self.membership_id is None
                    or self.authority_tenant_id != self.tenant_id
                    or self.authority_membership_id != self.membership_id
                    or self.group_id is not None
                    or self.management_relation_id is not None
                ):
                    raise ValueError("直属主体必须由当前租户的同一成员提供权限，不能带集团关系")
            elif self.access_mode is TenantAccessMode.GROUP_MANAGED:
                if (
                    self.membership_id is not None
                    or self.dept_id is not None
                    or self.authority_tenant_id is None
                    or self.authority_tenant_id == self.tenant_id
                    or self.authority_membership_id is None
                    or self.group_id is None
                    or self.management_relation_id is None
                ):
                    raise ValueError("托管主体必须明确集团/关系及外部权限来源，不能伪造直属成员")
            else:
                raise ValueError("Tenant 主体必须声明访问模式")
        if not tenant and self.effective_capabilities:
            raise ValueError("租户权益不能赋予账号或平台主体")
        if (self.realm in {SecurityRealm.PLATFORM, SecurityRealm.SUPPORT}) != (
            self.platform_operator_id is not None
        ):
            raise ValueError("平台操作身份必须与 realm 对应")
        if (self.realm is SecurityRealm.SUPPORT) != (self.support_session_id is not None):
            raise ValueError("支持会话必须与 realm 对应")
        if self.realm is SecurityRealm.SUPPORT:
            if self.approved_resource is None or self.approved_action != "read":
                raise ValueError("支持会话必须绑定获批的只读资源")
        elif self.approved_resource is not None or self.approved_action is not None:
            raise ValueError("非支持主体不能携带支持审批")
        return self

    def __repr_args__(self):
        return iter(())
