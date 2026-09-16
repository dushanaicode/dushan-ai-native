from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_job.core.job_registry import JobRegistry
from framework.starter_job.core.job_runtime import JobRuntime
from framework.starter_job.core.job_service import JobService
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.spi.job_definition_provider import JobDefinitionProvider
from framework.starter_job.spi.job_record_provider import JobRecordProvider
from framework.starter_job.spi.job_request_provider import JobRequestProvider
from framework.starter_job.spi.tenant_job_target_provider import TenantJobTargetProvider
from framework.starter_monitor.core.monitor_service import MonitorService
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum


class JobStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if JobSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(JobSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise JobException("configuration")
            yield
            return
        selected = {
            item.component
            for item in application.container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        handlers = [
            handler
            for handler in definitions.scan_result.get_components()
            if "__job__" in vars(handler) and CandidateSelection.qualified_name(handler) in selected
        ]
        registry = JobRegistry(
            handlers,
            ctx.date_utils.get_timezone_name() if settings.timezone is None else settings.timezone,
        )
        if not settings.enabled:
            yield
            return
        if (
            ctx.app.state.database is None
            or ctx.app.state.cache is None
            or ctx.app.state.security is None
        ):
            raise JobException("configuration")
        root = ctx.bootstrap_config.get_config(ApplicationSettings)
        workers = (
            root.granian.workers
            if ctx.settings.engine is ServerEngineEnum.GRANIAN
            else root.uvicorn.workers
        )
        if settings.owner_enabled and not root.server.reload and workers != 1:
            raise JobException("configuration")
        runtime = JobRuntime(
            settings,
            application,
            registry,
            application.container.get_optional(JobDefinitionProvider),
            application.container.get_optional(JobRequestProvider),
            application.container.get_optional(JobRecordProvider),
            ctx.app.state.security,
            application.container.get(CacheHandler),
            ctx.app.state.tenant,
            application.container.get_optional(TenantJobTargetProvider),
            application.container.get(MonitorService),
        )
        service = application.container.get(JobService)
        primary = None
        try:
            service.runtime = runtime
            ctx.app.state.job = runtime
            await runtime.open()
            yield
        except BaseException as error:
            primary = error
        finally:
            service.runtime = None
            ctx.app.state.job = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                runtime.close, "Job 调度与执行排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "Job 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
