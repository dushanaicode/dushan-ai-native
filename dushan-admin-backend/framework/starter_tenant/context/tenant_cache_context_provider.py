from framework.starter_cache.spi.tenant_context_provider import TenantContextProvider
from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_tenant.context.tenant_context import TenantContext


@framework(interface=TenantContextProvider, scope=ComponentScopeEnum.SINGLETON)
class TenantCacheContextProvider(TenantContextProvider):
    """Cache 只依赖自己的 SPI，不反向导入 Tenant。"""

    def __init__(self, context: TenantContext):
        self.context = context

    def get_required_tenant_id(self) -> str:
        return self.context.get_required_tenant_id()
