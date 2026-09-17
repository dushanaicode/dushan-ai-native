from loguru import logger

from framework.starter_data_permission.config.data_permission_settings import DataPermissionSettings
from framework.starter_data_permission.core.data_permission_policy import DataPermissionPolicy
from framework.starter_data_permission.core.data_permission_registry import DataPermissionRegistry
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_data_permission.spi.data_exemption_provider import DataExemptionProvider
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import starter
from framework.starter_di.decorators.conditional import conditional


@starter
@conditional(lambda config: config.get_config(DataPermissionSettings).enabled)
class DataPermissionStarter:
    """装配记录范围模型、豁免提供器及过滤/写入策略，排空后撤销绑定。"""

    def __init__(
        self,
        application: ApplicationContext,
        service: DataPermissionService,
        settings: DataPermissionSettings,
    ):
        self.application, self.service, self.settings = application, service, settings
        self._policy_scope = None

    def open(self, models, database):
        registry = DataPermissionRegistry(models)
        self.service.exemptions = self.application.container.get_optional(DataExemptionProvider)
        policy = DataPermissionPolicy(registry, self.service)
        self._policy_scope = database.use_session_policy(policy)
        self._policy_scope.__enter__()
        logger.info(
            "【DataPermissionStarter 】装配完成：会话过滤与写入校验策略已挂载，缓存={}，豁免提供器={}",
            self.settings.cache_enabled,
            self.service.exemptions is not None,
        )

    async def close(self):
        try:
            await self.service.close()
        finally:
            if self._policy_scope is not None:
                self._policy_scope.__exit__(None, None, None)
                self._policy_scope = None
        logger.info("【DataPermissionStarter 】数据权限资源已关闭")
