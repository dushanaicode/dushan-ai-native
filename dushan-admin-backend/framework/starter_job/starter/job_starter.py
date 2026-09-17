from loguru import logger

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.decorators.components import starter
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


@starter
class JobStarter:
    """注册选中的任务处理器、接入持久化 SPI 并创建应用独占的调度运行时。"""

    def __init__(self, settings: JobSettings, application: ApplicationContext, service: JobService):
        self.settings, self.application, self.service = settings, application, service
        self.runtime = None

    async def open(
        self, *, components, timezone, workers, reload, database, cache, security, tenant
    ):
        container = self.application.container
        selected = {
            item.component
            for item in container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        handlers = [
            item
            for item in components
            if "__job__" in vars(item) and CandidateSelection.qualified_name(item) in selected
        ]
        registry = JobRegistry(
            handlers, timezone if self.settings.timezone is None else self.settings.timezone
        )
        if not self.settings.enabled:
            logger.info("【JobStarter 】任务调度未启用")
            return None
        if database is None or cache is None or security is None:
            raise JobException("configuration")
        if self.settings.owner_enabled and not reload and workers != 1:
            raise JobException("configuration")
        self.runtime = JobRuntime(
            self.settings,
            self.application,
            registry,
            container.get_optional(JobDefinitionProvider),
            container.get_optional(JobRequestProvider),
            container.get_optional(JobRecordProvider),
            security,
            container.get(CacheHandler),
            tenant,
            container.get_optional(TenantJobTargetProvider),
            container.get(MonitorService),
        )
        self.service.runtime = self.runtime
        logger.debug("【JobStarter 】运行时 SPI 已绑定，timezone={}", registry.timezone)
        await self.runtime.open()
        return self.runtime

    async def activate(self):
        await self.runtime.activate()

    async def close(self):
        if self.runtime is not None:
            self.service.runtime = None
            await self.runtime.close()
            logger.info("【JobStarter 】调度与执行资源已关闭")
