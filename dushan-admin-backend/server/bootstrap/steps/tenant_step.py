from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_tenant.config.tenant_settings import TenantSettings
from framework.starter_tenant.core.tenant_model_discovery import TenantModelDiscovery
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_service import TenantService
from framework.starter_tenant.core.tenant_session_policy import TenantSessionPolicy
from framework.starter_tenant.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.deployment_mode_record import DeploymentModeRecord
from framework.starter_tenant.model.tenant_model import TenantModel
from framework.starter_tenant.spi.tenant_directory_provider import TenantDirectoryProvider
from framework.starter_tenant.spi.tenant_provisioning_provider import TenantProvisioningProvider


class TenantStep:
    """模式只在启动期读取；无数据库的骨架可启动，但租户资源不可执行。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if TenantSettings not in definitions.configuration.model_classes:
            yield
            return
        models = [
            model
            for model in TenantModelDiscovery.collect(
                tuple(module.definition.package for module in definitions.modules),
                definitions.scan_result.get_components(),
            )
            if model is not DeploymentModeRecord
        ]
        registry = TenantModelRegistry(
            [*models, TenantModel(DeploymentModeRecord, TenantModelKind.GLOBAL, None)]
        )
        application = definitions.application_context
        if application is None:
            if models:
                raise TenantException("configuration")
            yield
            return
        service = application.container.get(TenantService)
        service.directory = application.container.get_optional(TenantDirectoryProvider)
        service.provisioning = application.container.get_optional(TenantProvisioningProvider)
        database = ctx.app.state.database
        if any(not item.public for item in registry.entries.values()) and (
            database is None or service.directory is None
        ):
            raise TenantException("configuration")
        primary = None
        try:
            ctx.app.state.tenant = service
            if database is None:
                yield
            else:
                await service.mode.claim()
                service.ready = service.directory is not None
                policy = TenantSessionPolicy(registry, service.context)
                with database.use_session_policy(policy):
                    yield
        except BaseException as error:
            primary = error
        finally:
            ctx.app.state.tenant = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                service.close, "租户执行排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "租户启动步骤失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
