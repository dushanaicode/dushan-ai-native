"""控制台日志的初始化与释放。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from server.bootstrap.context import AppBootstrapContext


@asynccontextmanager
async def configure_logging(ctx: AppBootstrapContext) -> AsyncIterator[None]:
    """不修改全局日志配置，不创建源码目录内的日志文件。"""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    ctx.logger.setLevel(ctx.settings.log_level)
    ctx.logger.addHandler(handler)
    try:
        yield
    finally:
        ctx.logger.removeHandler(handler)
        handler.close()
