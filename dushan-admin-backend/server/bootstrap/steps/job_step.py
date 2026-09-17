from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_job.exception.job_exception import JobException
from framework.starter_job.starter.job_starter import JobStarter
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum


class JobStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if JobSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【JobStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(JobSettings)
        application = definitions.application_context
        if application is None:
            if settings.enabled:
                raise JobException("configuration")
            ctx.logger.info("【JobStarter 】任务调度未启用")
            yield
            return
        root = ctx.bootstrap_config.get_config(ApplicationSettings)
        workers = (
            root.granian.workers
            if ctx.settings.engine is ServerEngineEnum.GRANIAN
            else root.uvicorn.workers
        )
        starter = application.container.get(JobStarter)
        activation = ("Job", starter.activate)
        primary = None
        try:
            ctx.app.state.job = await starter.open(
                components=definitions.scan_result.get_components(),
                timezone=ctx.date_utils.get_timezone_name(),
                workers=workers,
                reload=root.server.reload,
                database=ctx.app.state.database,
                cache=ctx.app.state.cache,
                security=ctx.app.state.security,
                tenant=ctx.app.state.tenant,
            )
            if ctx.app.state.job is not None:
                ctx.before_ready.append(activation)
            yield
        except BaseException as error:
            primary = error
        finally:
            if activation in ctx.before_ready:
                ctx.before_ready.remove(activation)
            ctx.app.state.job = None
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "Job 调度与执行排空"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "Job 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
