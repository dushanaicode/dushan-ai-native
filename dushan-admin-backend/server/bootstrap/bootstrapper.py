from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager

from framework.common.utils.cleanup_utils import CleanupUtils
from server.bootstrap.context import AppBootstrapContext
from server.bootstrap.step_registry import APP_BOOTSTRAP_STEPS, BootstrapStepSpec
from server.bootstrap.step_runner import BootstrapStepRunner


class BootstrapError(RuntimeError):
    """启动步骤执行失败，报错时保留步骤名称和原始异常。"""


@asynccontextmanager
async def bootstrap_app(
    ctx: AppBootstrapContext, steps: Sequence[BootstrapStepSpec] | None = None
) -> AsyncIterator[None]:
    """按顺序启动服务，退出时倒序清理。

    中途启动失败时，只清理已成功进入的步骤；某一步清理报错后，
    仍会继续清理剩余步骤。退出先受保护地等待业务排空完成，宿主取消
    在排空后再传播，资源步骤不会在业务仍使用时被释放。
    """
    selected = APP_BOOTSTRAP_STEPS if steps is None else steps
    try:
        async with AsyncExitStack() as resources:
            for step in selected:
                try:
                    await resources.enter_async_context(BootstrapStepRunner.run(ctx, step))
                except Exception as error:
                    raise BootstrapError(f"启动步骤「{step.name}」失败") from error
            if ctx.definitions is not None and ctx.definitions.application_context is not None:
                ctx.definitions.application_context.mark_ready()
            primary = None
            try:
                for name, activate in ctx.before_ready:
                    try:
                        await activate()
                    except Exception as error:
                        raise BootstrapError(f"启动激活「{name}」失败") from error
                ctx.ready = True
                ctx.logger.info("服务已就绪")
                yield
            except BaseException as error:
                primary = error
                raise
            finally:
                ctx.ready = False
                ctx.logger.info("【Bootstrapper 】服务正在关闭")
                errors = []
                caller_cancellation = None
                # 长连接/消息入口先停止接收并排空；此时 DI 和发布连接仍可完成必要收尾。
                for quiesce in reversed(ctx.before_drain):
                    error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                        quiesce, "外部入口停止接收"
                    )
                    if error is not None:
                        errors.append(error)
                    if caller_cancellation is None:
                        caller_cancellation = cancellation
                if ctx.definitions is not None and ctx.definitions.application_context is not None:
                    # 公开 drain 允许调用方取消；这里是资源所有者，必须等到排空终态。
                    error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                        ctx.definitions.application_context.drain, "应用业务排空"
                    )
                    if error is not None:
                        errors.append(error)
                    if caller_cancellation is None:
                        caller_cancellation = cancellation
                CleanupUtils.raise_collected_cleanup_errors(
                    "应用业务排空失败",
                    errors,
                    caller_cancellation=caller_cancellation,
                    primary_error=primary,
                )
    finally:
        ctx.ready = False
