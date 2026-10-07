from loguru import logger

from framework.common.utils.cleanup_utils import CleanupUtils
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.decorators.components import starter
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.password_encoder import PasswordEncoder
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.spi.data_access_provider import DataAccessProvider
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider
from framework.starter_security.spi.public_request_context_provider import (
    PublicRequestContextProvider,
)
from framework.starter_security.spi.request_access_provider import RequestAccessProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider


@starter
class SecurityStarter:
    """接入身份 SPI、Web 授权、数据库审计与业务日志，并按依赖反序释放。"""

    def __init__(
        self,
        application: ApplicationContext,
        settings: SecuritySettings,
        passwords: PasswordEncoder,
    ):
        self.application, self.settings, self.passwords = application, settings, passwords
        self.service = self.audit = None
        self._routes = None

    async def open(self, *, routes, database, expression_utils):
        self._routes = routes
        self._previous_access = routes.access_provider
        self._previous_validator = routes.policy_validator
        self._previous_public_parameters = routes.public_context_parameters
        if not self.settings.enabled:
            logger.info("【SecurityStarter】本站安全未启用")
            return
        if self._previous_access is not None and not isinstance(
            self._previous_access, SecurityAccess
        ):
            raise ValueError("Security 与宿主授权提供者声明冲突")
        container = self.application.container
        self.service = container.get(SecurityService)
        request_access = container.get_optional(RequestAccessProvider)
        await self.service.open(
            tenant=container.get_optional(TenantAccessProvider),
            messages=container.get_optional(MessageSecurityProvider),
            workloads=container.get_optional(WorkloadProvider),
            data_access=container.get_optional(DataAccessProvider),
            request_access=request_access,
        )
        public_contexts = container.get_optional(PublicRequestContextProvider)
        access = SecurityAccess(public_contexts, self.service, request_access)
        routes.access_provider = access
        routes.policy_validator = access.validate_policy
        routes.public_context_parameters = (
            None if public_contexts is None else public_contexts.parameters
        )
        logger.info("【SecurityStarter】Web 授权与路由策略验证已接入")
        if database is not None:
            database.bind_account_provider(container.get(SecurityContext))
        if self.settings.bizlog_enabled:
            logger.info("【SecurityStarter】开始装配业务审计")
            expression_utils.render_text("", {})
            self.audit = container.get(BizLogService)
            logger.info("【SecurityStarter】业务审计装配完成")
        else:
            logger.info("【SecurityStarter】业务审计未启用")

    async def close(self):
        if self._routes is not None:
            self._routes.access_provider = self._previous_access
            self._routes.policy_validator = self._previous_validator
            self._routes.public_context_parameters = self._previous_public_parameters
        errors, cancellation = [], None
        for resource in (self.audit, self.service, self.passwords):
            if resource is None:
                continue
            error, cancelled = await CleanupUtils.run_cancellation_safe_cleanup(
                resource.close, "Security 资源排空"
            )
            if error is not None:
                errors.append(error)
            if cancelled is not None:
                cancellation = cancelled
        CleanupUtils.raise_collected_cleanup_errors(
            "Security 关闭失败", errors, caller_cancellation=cancellation
        )
        if self.settings.enabled:
            logger.info("【SecurityStarter】安全资源已关闭")
