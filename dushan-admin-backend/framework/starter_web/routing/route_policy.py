from dataclasses import dataclass
from typing import ClassVar

from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode


@dataclass(frozen=True, slots=True)
class RoutePolicy:
    """明确公开或要求认证；可装饰原生端点/路由器，None 只代表尚未声明。"""

    ATTRIBUTE: ClassVar[str] = "__web_access_policy__"
    permissions: tuple[str, ...] = ()
    tenant_required: bool = False
    requires_identity: bool = True
    roles: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    realm: SecurityRealm | None = None
    domain: str | None = None
    permission_mode: str = "all"
    role_mode: str = "all"
    scope_mode: str = "all"
    allowed_tenant_access_modes: frozenset[TenantAccessMode] | None = None
    required_capability: str | None = None
    required_entitlement: str | None = None
    required_support_resource: str | None = None
    required_support_action: str | None = None

    @staticmethod
    def resolve(
        inherited: "RoutePolicy | None", declared: "RoutePolicy | None"
    ) -> "RoutePolicy | None":
        """保护声明只能继承或一致重复；公开容器可增加保护但不能丢失部署能力。"""
        if inherited is not None and declared is not None and inherited != declared:
            if (
                inherited.requires_identity
                or not declared.requires_identity
                or (
                    inherited.required_capability is not None
                    and inherited.required_capability != declared.required_capability
                )
            ):
                raise ValueError("外层与内层访问声明冲突")
        return inherited if declared is None else declared

    @classmethod
    def public(cls) -> "RoutePolicy":
        return cls(requires_identity=False)

    def __call__(self, owner):
        previous = getattr(owner, self.ATTRIBUTE, None)
        if previous is not None and previous != self:
            raise ValueError("公开/保护声明冲突")
        setattr(owner, self.ATTRIBUTE, self)
        return owner

    def __post_init__(self) -> None:
        if type(self.requires_identity) is not bool or type(self.tenant_required) is not bool:
            raise TypeError("公开和租户声明必须是布尔值")
        if not self.requires_identity and (
            self.permissions
            or self.tenant_required
            or self.roles
            or self.scopes
            or self.realm
            or self.domain
            or self.allowed_tenant_access_modes
            or self.required_entitlement
            or self.required_support_resource
            or self.required_support_action
        ):
            raise ValueError("公开路由不能声明权限或必需租户")
        for values in (self.permissions, self.roles, self.scopes):
            if not isinstance(values, tuple) or any(
                not isinstance(item, str) or not item or item != item.strip() for item in values
            ):
                raise ValueError("权限声明必须是非空规范字符串元组")
            if len(values) != len(set(values)):
                raise ValueError("权限声明不能重复")
        if self.realm is not None and not isinstance(self.realm, SecurityRealm):
            raise TypeError("realm 必须使用 SecurityRealm")
        if self.domain is not None and (not self.domain or self.domain != self.domain.strip()):
            raise ValueError("认证域声明无效")
        if any(
            mode not in {"all", "any"}
            for mode in (self.permission_mode, self.role_mode, self.scope_mode)
        ):
            raise ValueError("权限、角色和 scope 组合策略必须是 all 或 any")
        if self.tenant_required and self.realm in {SecurityRealm.ACCOUNT, SecurityRealm.PLATFORM}:
            raise ValueError("账号或平台路由不能要求租户权限")
        for value in (
            self.required_capability,
            self.required_entitlement,
            self.required_support_resource,
        ):
            if value is not None and (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value) > 256
            ):
                raise ValueError("能力、权益和资源声明必须使用明确的代码")
        if self.realm is SecurityRealm.TENANT and self.allowed_tenant_access_modes is None:
            object.__setattr__(
                self, "allowed_tenant_access_modes", frozenset({TenantAccessMode.DIRECT_MEMBERSHIP})
            )
        if self.allowed_tenant_access_modes is not None:
            if (
                self.realm is not SecurityRealm.TENANT
                or not isinstance(self.allowed_tenant_access_modes, frozenset)
                or not self.allowed_tenant_access_modes
                or any(
                    not isinstance(mode, TenantAccessMode)
                    for mode in self.allowed_tenant_access_modes
                )
            ):
                raise ValueError("租户访问模式只能用于明确的 Tenant 路由，且不能为空")
        if self.required_entitlement is not None and self.realm not in {
            SecurityRealm.TENANT,
            SecurityRealm.SUPPORT,
        }:
            raise ValueError("租户权益只适用于 Tenant/Support 路由")
        if self.realm is SecurityRealm.SUPPORT:
            if (
                self.required_capability != "support_session"
                or self.required_entitlement != "support_session"
                or self.required_support_resource is None
                or self.required_support_action != "read"
            ):
                raise ValueError("Support 路由必须声明支持能力/权益以及获批的只读资源")
        elif self.required_support_resource is not None or self.required_support_action is not None:
            raise ValueError("支持资源与动作只适用于 Support 路由")
