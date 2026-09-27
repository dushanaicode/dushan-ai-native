from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_tenant.core.tenant_service import TenantService


@framework(interface=TenantAccessProvider, scope=ComponentScopeEnum.SINGLETON)
class TenantAccessProviderAdapter(TenantAccessProvider):
    """向安全组件发布租户准入 SPI，原服务继续负责完整作用域。"""

    def __init__(self, service: TenantService):
        self.service = service

    @property
    def is_ready(self) -> bool:
        return self.service.is_ready

    def supports(self, capability):
        return self.service.supports(capability)

    def enter(self, session, policy):
        return self.service.enter(session, policy)

    def enter_workload(self, identity, capability):
        return self.service.enter_workload(identity, capability)
