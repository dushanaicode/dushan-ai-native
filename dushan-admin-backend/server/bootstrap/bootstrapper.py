"""按顺序启动，按逆序清理应用资源。"""

from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager

from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS, BootstrapStepSpec


class BootstrapError(RuntimeError):
    """标明失败的启动步骤，并保留原异常链。"""


@asynccontextmanager
async def bootstrap_app(
    ctx: AppBootstrapContext, steps: Sequence[BootstrapStepSpec] | None = None
) -> AsyncIterator[None]:
    """启动失败只清理已进入的步骤，关闭异常不会跳过其余清理。"""
    selected = APP_BOOTSTRAP_STEPS if steps is None else steps
    try:
        # ponytail: 当前仅配置与日志；接入外部资源前补齐清理超时和重复取消处理。
        async with AsyncExitStack() as resources:
            for step in selected:
                try:
                    await resources.enter_async_context(step.handler(ctx))
                except Exception as error:
                    raise BootstrapError(f"启动步骤「{step.name}」失败") from error
            ctx.ready = True
            ctx.logger.info("服务已就绪：%s，环境：%s", ctx.settings.name, ctx.settings.env.value)
            try:
                yield
            finally:
                ctx.ready = False
                ctx.logger.info("服务正在关闭")
    finally:
        ctx.ready = False
