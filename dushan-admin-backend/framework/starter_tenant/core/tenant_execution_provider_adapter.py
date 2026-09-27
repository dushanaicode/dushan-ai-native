from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_tenant.spi.tenant_execution_provider import TenantExecutionProvider


@framework(interface=TenantExecutionProvider, scope=ComponentScopeEnum.SINGLETON)
class TenantExecutionProviderAdapter(TenantExecutionProvider):
    """发布同一租户服务的执行能力，实例启停仍归 TenantStarter。"""

    def __init__(self, service: TenantService):
        self.service = service

    @property
    def ready(self) -> bool:
        return self.service.ready

    @property
    def context(self):
        return self.service.context

    def target_batches(self):
        return self.service.target_batches()
