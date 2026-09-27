import asyncio

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_job.config.job_settings import JobSettings
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_websocket.config.websocket_settings import WebSocketSettings
from server.bootstrap.context import AppBootstrapContext


class ApplicationHealth:
    """汇总已装配且启用的必要资源；缺失运行实例不是关闭开关。"""

    PROBE_TIMEOUT_SECONDS = 2.0  # 小于容器 /health 请求的 3 秒超时。

    @classmethod
    async def check(cls, ctx: AppBootstrapContext) -> dict[str, bool]:
        state = ctx.app.state
        components = {"bootstrap": ctx.ready and state.web_routes.published}
        if not ctx.ready or ctx.definitions is None:
            return components
        configuration = ctx.definitions.configuration
        probes = {}
        runtimes = {}
        for name, model, runtime in (
            ("database", DatabaseSettings, state.database),
            ("cache", CacheSettings, state.cache),
            ("job", JobSettings, state.job),
            ("mq", MQSettings, state.mq),
            ("websocket", WebSocketSettings, state.websocket),
        ):
            if (
                model not in configuration.model_classes
                or not configuration.get_config(model).enabled
            ):
                continue
            runtimes[name] = runtime
            components[name] = runtime is not None and runtime.is_ready
            if components[name] and name in {"cache", "mq"}:
                probes[name] = cls._probe(ctx, name, runtime)
        results = await asyncio.gather(*probes.values())
        components.update(zip(probes, results, strict=True))
        components["bootstrap"] = ctx.ready and state.web_routes.published
        for name, runtime in runtimes.items():
            components[name] = components[name] and runtime is not None and runtime.is_ready
        return components

    @staticmethod
    async def _probe(ctx, name, runtime) -> bool:
        try:
            async with asyncio.timeout(ApplicationHealth.PROBE_TIMEOUT_SECONDS):
                return await runtime.check_health()
        except Exception as error:
            # 健康边界把资源探测失败明确转换为不就绪；取消仍向调用方传播。
            ctx.logger.warning(
                "健康检查失败 component={} error_type={}", name, type(error).__name__
            )
            return False
