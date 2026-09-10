from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager

from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS, BootstrapStepSpec


class BootstrapError(RuntimeError):
    """启动步骤执行失败，报错时保留步骤名称和原始异常。"""


@asynccontextmanager
async def bootstrap_app(
    ctx: AppBootstrapContext, steps: Sequence[BootstrapStepSpec] | None = None
) -> AsyncIterator[None]:
    """按顺序启动服务，退出时倒序清理。

    中途启动失败时，只清理已成功进入的步骤；某一步清理报错后，
    仍会继续清理剩余步骤。
    """
    selected = APP_BOOTSTRAP_STEPS if steps is None else steps
    try:
        # ponytail: 已接配置、日志和 i18n；加入数据库等资源时再补清理超时与重复取消处理。
        async with AsyncExitStack() as resources:
            for step in selected:
                try:
                    await resources.enter_async_context(step.handler(ctx))
                except Exception as error:
                    raise BootstrapError(f"启动步骤「{step.name}」失败") from error
            ctx.ready = True
            ctx.logger.info("服务已就绪：{}，环境：{}", ctx.settings.name, ctx.settings.env.value)
            try:
                yield
            finally:
                ctx.ready = False
                ctx.logger.info("服务正在关闭")
    finally:
        ctx.ready = False
