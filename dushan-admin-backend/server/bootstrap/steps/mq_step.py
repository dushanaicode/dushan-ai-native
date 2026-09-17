from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.starter.mq_starter import MQStarter


class MQStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if MQSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【MQStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(MQSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise MQException("configuration")
            ctx.logger.info("【MQStarter 】消息队列未启用")
            yield
            return
        starter = application.container.get(MQStarter)
        activation = ("MQ", starter.activate)
        runtime = primary = None
        try:
            runtime = await starter.open(
                components=definitions.scan_result.get_components(),
                cache=ctx.app.state.cache,
                security=ctx.app.state.security,
                tenant=ctx.app.state.tenant,
                database=ctx.app.state.database,
                job=ctx.app.state.job,
            )
            ctx.app.state.mq = runtime
            if runtime is not None:
                # Job 可依赖 MQ 发布消息，因此消费者先激活，调度器再恢复运行。
                ctx.before_ready.insert(0, activation)
                ctx.before_drain.append(runtime.quiesce)
            yield
        except BaseException as error:
            primary = error
        finally:
            if activation in ctx.before_ready:
                ctx.before_ready.remove(activation)
            if runtime is not None and runtime.quiesce in ctx.before_drain:
                ctx.before_drain.remove(runtime.quiesce)
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "MQ 消费排空与连接关闭"
            )
            ctx.app.state.mq = None
            CleanupUtils.raise_collected_cleanup_errors(
                "MQ 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
