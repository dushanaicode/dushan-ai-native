from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_di.core.candidate_selection import CandidateSelection
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


class MQStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if MQSettings not in definitions.configuration.model_classes:
            yield
            return
        settings = definitions.configuration.get_config(MQSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise MQException("configuration")
            yield
            return
        selected = {
            item.component
            for item in application.container.get_binding_diagnostics()
            if item.outcome is BindingOutcomeEnum.SELECTED
        }
        components = [
            component
            for component in definitions.scan_result.get_components()
            if CandidateSelection.qualified_name(component) in selected
        ]
        handlers = [component for component in components if "__mq_consumer__" in vars(component)]
        registry = ConsumerRegistry(settings, handlers)
        if not settings.enabled:
            registry.apply(settings.overrides)
            yield
            return
        if (
            ctx.app.state.cache is None
            or ctx.app.state.security is None
            or application.container.get_optional(MessageSecurityProvider) is None
        ):
            raise MQException("configuration")
        if settings.outbox_enabled and (
            ctx.app.state.database is None or ctx.app.state.job is None
        ):
            raise MQException("configuration")
        overrides = application.container.get_optional(ConsumerOverrideProvider)
        changes = {} if overrides is None else await overrides.load()
        registry.apply({**changes, **settings.overrides})
        runtime = MQRuntime(
            settings,
            application,
            registry,
            application.container.get(CacheHandler),
            ctx.app.state.security,
            ctx.app.state.tenant,
            ctx.app.state.database,
            application.container.get(MonitorService),
            application.container.get_optional(ConsumeRecordProvider),
            [component for component in components if "__mq_interceptor__" in vars(component)],
        )
        runtime.outbox = (
            application.container.get_optional(OutboxProvider) if settings.outbox_enabled else None
        )
        if settings.outbox_enabled and runtime.outbox is None:
            raise MQException("configuration")
        service = application.container.get(MQService)
        primary = None
        try:
            service.runtime = runtime
            ctx.app.state.mq = runtime
            await runtime.open()
            ctx.before_drain.append(runtime.quiesce)
            yield
        except BaseException as error:
            primary = error
        finally:
            if runtime.quiesce in ctx.before_drain:
                ctx.before_drain.remove(runtime.quiesce)
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                runtime.close, "MQ 消费排空与连接关闭"
            )
            service.runtime = None
            ctx.app.state.mq = None
            CleanupUtils.raise_collected_cleanup_errors(
                "MQ 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
