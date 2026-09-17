from contextlib import asynccontextmanager

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.starter.websocket_starter import WebSocketStarter
from server.config.application_settings import ApplicationSettings
from server.enums.server_engine_enum import ServerEngineEnum


class WebSocketStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        if WebSocketSettings not in definitions.configuration.model_classes:
            ctx.logger.info("【WebSocketStarter 】配置模型未装配，跳过启动")
            yield
            return
        settings = definitions.configuration.get_config(WebSocketSettings)
        if not settings.enabled:
            ctx.logger.info("【WebSocketStarter 】WebSocket 未启用")
            yield
            return
        application = definitions.application_context
        if application is None:
            raise SocketException("configuration")
        root = ctx.bootstrap_config.get_config(ApplicationSettings)
        workers = (
            root.granian.workers
            if ctx.settings.engine is ServerEngineEnum.GRANIAN
            else root.uvicorn.workers
        )
        starter = application.container.get(WebSocketStarter)
        runtime = primary = None
        try:
            runtime = await starter.open(
                components=definitions.scan_result.get_components(),
                security=ctx.app.state.security,
                cache_available=ctx.app.state.cache,
                routes=ctx.app.state.web_routes,
                translator=definitions.translator,
                proxies=definitions.configuration.get_config(IpSettings).trusted_proxy_cidrs,
                logging_owner=ctx.logging_owner,
                workers=workers,
                reload=root.server.reload,
            )
            ctx.app.state.websocket = runtime
            ctx.before_drain.append(runtime.quiesce)
            yield
        except BaseException as error:
            primary = error
        finally:
            if runtime is not None and runtime.quiesce in ctx.before_drain:
                ctx.before_drain.remove(runtime.quiesce)
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                starter.close, "WebSocket 关闭"
            )
            ctx.app.state.websocket = None
            CleanupUtils.raise_collected_cleanup_errors(
                "WebSocket 启停失败",
                [] if error is None else [error],
                primary_error=primary,
                caller_cancellation=cancellation,
            )
