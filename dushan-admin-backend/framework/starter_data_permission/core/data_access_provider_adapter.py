from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.spi.data_access_provider import DataAccessProvider


@framework(interface=DataAccessProvider, scope=ComponentScopeEnum.SINGLETON)
@conditional(lambda config: config.get_config(DataPermissionSettings).enabled)
class DataAccessProviderAdapter(DataAccessProvider):
    """复用当前数据权限实例和原上下文管理器，保持退出与取消清理顺序。"""

    def __init__(self, service: DataPermissionService):
        self.service = service

    def enter(self, identity, *, capability=None):
        """传递本次执行能力，由数据权限服务建立并释放资源豁免。"""
        return self.service.enter(identity, capability=capability)
