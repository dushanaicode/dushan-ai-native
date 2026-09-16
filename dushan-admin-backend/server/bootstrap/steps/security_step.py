from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_data_permission.core.data_permission_service import DataPermissionService
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.core.password_encoder import PasswordEncoder
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.integration.security_access import SecurityAccess
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider
from framework.starter_security.spi.tenant_access_provider import TenantAccessProvider
from framework.starter_security.spi.workload_provider import WorkloadProvider
from server.bootstrap.context import AppBootstrapContext


class SecurityStep:
    """数据库/缓存就绪后启用 Security，业务排空后先关闭 Security 再释放依赖。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext):
        definitions = ctx.definitions
        if SecuritySettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(SecuritySettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise ValueError("启用 Security 要求先启用 DI")
            yield
            return
        passwords = application.container.get(PasswordEncoder)
        service = audit = None
        routes = ctx.app.state.web_routes
        original_access = routes.access_provider
        original_validator = routes.policy_validator
        primary = None
        try:
            if settings.enabled:
                if original_access is not None and not isinstance(original_access, SecurityAccess):
                    raise ValueError("Security 与宿主授权提供者声明冲突")
                service = application.container.get(SecurityService)
                # 已装配 Tenant 使用其唯一运行时；独立 Security 装配仍通过正式 SPI。
                tenant = ctx.app.state.tenant
                if tenant is None:
                    tenant = application.container.get_optional(TenantAccessProvider)
                await service.open(
                    tenant=tenant,
                    messages=application.container.get_optional(MessageSecurityProvider),
                    workloads=application.container.get_optional(WorkloadProvider),
                    data_access=application.container.get_optional(DataPermissionService),
                )
                ctx.app.state.security = service
                routes.access_provider = SecurityAccess()
                routes.policy_validator = service.validate_policy
                if ctx.app.state.database is not None:
                    ctx.app.state.database.bind_account_provider(
                        application.container.get(SecurityContext)
                    )
                if settings.bizlog_enabled:
                    # 模板复用现有受限表达式能力；配置不完整必须在业务就绪前失败。
                    ctx.expression_utils.render_text("", {})
                    audit = application.container.get(BizLogService)
            yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.security = None
            routes.access_provider = original_access
            routes.policy_validator = original_validator
            errors, cancellation = [], None
            for resource in (audit, service, passwords):
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
                "Security 启停失败",
                errors,
                primary_error=primary,
                caller_cancellation=cancellation,
            )
