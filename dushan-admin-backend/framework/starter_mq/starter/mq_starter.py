from loguru import logger

from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.candidate_selection import CandidateSelection
from framework.starter_di.decorators.components import starter
from framework.starter_di.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_mq.core.consumer_registry import ConsumerRegistry
from framework.starter_mq.core.mq_runtime import MQRuntime
from framework.starter_mq.core.mq_service import MQService
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.spi.consume_record_provider import ConsumeRecordProvider
from framework.starter_mq.spi.consumer_override_provider import ConsumerOverrideProvider
from framework.starter_mq.spi.outbox_provider import OutboxProvider
from framework.starter_security.spi.message_security_provider import MessageSecurityProvider


@starter
class MQStarter:
    """合并消费者声明与业务覆盖，绑定拦截器和 Outbox，再启动传输资源。"""

    def __init__(self, settings: MQSettings, application: ApplicationContext, service: MQService):
        self.settings, self.application, self.service = settings, application, service
        self.runtime = None

    async def open(self, *, components, cache, security, tenant, database, job):
        container = self.application.container
        selected = {
            item.component
            for item in container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        components = [
            item for item in components if CandidateSelection.qualified_name(item) in selected
        ]
        handlers = [item for item in components if "__mq_consumer__" in vars(item)]
        registry = ConsumerRegistry(self.settings, handlers)
        self.service.declarations = tuple(item.__mq_consumer__ for item in handlers)
        if not self.settings.enabled:
            registry.apply(self.settings.overrides)
            logger.info("【MQStarter 】消息队列未启用")
            return None
        if (
            cache is None
            or security is None
            or container.get_optional(MessageSecurityProvider) is None
        ):
            raise MQException("configuration")
        if self.settings.outbox_enabled and (database is None or job is None):
            raise MQException("configuration")
        overrides = container.get_optional(ConsumerOverrideProvider)
        changes = {} if overrides is None else await overrides.load()
        registry.apply({**changes, **self.settings.overrides})
        self.runtime = MQRuntime(
            self.settings,
            self.application,
            registry,
            container.get(CacheHandler),
            security,
            tenant,
            database,
            container.get(MonitorService),
            container.get_optional(ConsumeRecordProvider),
            [item for item in components if "__mq_interceptor__" in vars(item)],
        )
        self.runtime.outbox = (
            container.get_optional(OutboxProvider) if self.settings.outbox_enabled else None
        )
        if self.settings.outbox_enabled and self.runtime.outbox is None:
            raise MQException("configuration")
        self.service.runtime = self.runtime
        logger.debug(
            "【MQStarter 】拦截器 {} 个，Outbox={}",
            len(self.runtime.interceptors),
            self.runtime.outbox is not None,
        )
        await self.runtime.open()
        return self.runtime

    async def activate(self):
        await self.runtime.activate()

    async def close(self):
        if self.runtime is not None:
            try:
                await self.runtime.close()
            finally:
                self.service.runtime = None
            logger.info("【MQStarter 】消息消费与传输资源已关闭")
