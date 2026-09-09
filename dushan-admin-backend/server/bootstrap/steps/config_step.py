"""将已校验配置绑定到应用。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from server.bootstrap.context import AppBootstrapContext


@asynccontextmanager
async def bind_server_config(ctx: AppBootstrapContext) -> AsyncIterator[None]:
    """关闭时撤下生命周期内发布的配置。"""
    ctx.app.state.server_settings = ctx.settings
    try:
        yield
    finally:
        del ctx.app.state.server_settings
