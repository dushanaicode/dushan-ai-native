from loguru import logger

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import starter
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_tenant.core.tenant_session_policy import TenantSessionPolicy
from framework.starter_tenant.definitions.constants.tenant_error_codes import TenantErrorCodes
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.spi.tenant_directory_provider import TenantDirectoryProvider
from framework.starter_tenant.spi.tenant_provisioning_provider import TenantProvisioningProvider


@starter
class TenantStarter:
    """登记模型归属、接入业务提供器并持有本应用的租户会话策略。"""

    def __init__(self, application: ApplicationContext, service: TenantService):
        self.application, self.service = application, service
        self._policy_scope = None

    def open(self, models, database):
        registry = TenantModelRegistry(models)
        self.service.directory = self.application.container.get_optional(TenantDirectoryProvider)
        self.service.provisioning = self.application.container.get_optional(
            TenantProvisioningProvider
        )
        if any(not item.public for item in registry.entries.values()) and (
            database is None or self.service.directory is None
        ):
            raise TenantException(TenantErrorCodes.CONFIGURATION)
        logger.info(
            "【TenantStarter 】提供器装配：租户目录={}，租户开通={}",
            self.service.directory is not None,
            self.service.provisioning is not None,
        )
        if database is None:
            logger.info("【TenantStarter 】模型装配完成，未启用数据库，租户会话策略未挂载")
            return
        self.service.ready = self.service.directory is not None
        self._policy_scope = database.use_session_policy(
            TenantSessionPolicy(registry, self.service.context)
        )
        self._policy_scope.__enter__()
        logger.info(
            "【TenantStarter 】装配完成：会话隔离策略已挂载，模型 {} 个，目录服务就绪={}",
            len(registry.entries),
            self.service.ready,
        )

    async def close(self):
        try:
            if self._policy_scope is not None:
                self._policy_scope.__exit__(None, None, None)
                self._policy_scope = None
        finally:
            await self.service.close()
        logger.info("【TenantStarter 】租户资源已关闭")
