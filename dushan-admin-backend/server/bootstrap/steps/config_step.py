from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from server.bootstrap.app_bootstrap_context import AppBootstrapContext


class ConfigStep:
    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext) -> AsyncIterator[None]:
        """把配置放到 app.state，退出时移除。"""
        ctx.app.state.server_settings = ctx.settings
        try:
            yield
        finally:
            del ctx.app.state.server_settings
