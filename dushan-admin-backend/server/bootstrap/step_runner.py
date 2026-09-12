from contextlib import asynccontextmanager, nullcontext

from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_di.enums.lifecycle_phase_enum import LifecyclePhaseEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException


class BootstrapStepRunner:
    """为实际资源步骤提供受限初始化/清理上下文，不改变步骤的资源所有权。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx, spec):
        application = None if ctx.definitions is None else ctx.definitions.application_context
        if spec.requires_di and application is None:
            raise DiException(
                error_code=DiErrorCodes.NOT_READY, msg=f"启动步骤要求先启用并装配 DI：{spec.name}"
            )
        manager = spec.handler(ctx)
        access = (
            nullcontext()
            if application is None
            else application._phase_access(LifecyclePhaseEnum.INITIALIZE)
        )
        with access:
            await manager.__aenter__()
        try:
            yield
        except BaseException as primary:
            if not await BootstrapStepRunner._exit(manager, application, spec.name, primary):
                raise
        else:
            await BootstrapStepRunner._exit(manager, application, spec.name, None)

    @staticmethod
    async def _exit(manager, application, name, primary):
        suppressed = False

        async def cleanup():
            nonlocal suppressed
            access = (
                nullcontext()
                if application is None
                else application._phase_access(LifecyclePhaseEnum.DESTROY)
            )
            with access:
                suppressed = await manager.__aexit__(
                    None if primary is None else type(primary),
                    primary,
                    None if primary is None else primary.__traceback__,
                )

        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
            cleanup, f"启动步骤清理：{name}"
        )
        if error is not None and primary is None and cancellation is None:
            raise error
        if error is not None or cancellation is not None:
            CleanupUtils.raise_collected_cleanup_errors(
                f"启动步骤清理失败：{name}",
                [] if error is None else [error],
                caller_cancellation=cancellation,
                primary_error=primary,
            )
        return suppressed
