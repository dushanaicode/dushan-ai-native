from contextlib import asynccontextmanager

from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_web.starter.web_starter import WebStarter


class WebStep:
    """让 Web Starter 发布活动路由，并在其他入口关闭前撤销发布。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx):
        definitions = ctx.definitions
        starter = WebStarter(ctx.app.state.web_routes)
        try:
            starter.open(
                components=definitions.scan_result.get_components(
                    component_type=ComponentTypeEnum.COMPONENT
                ),
                application=definitions.application_context,
                configuration=definitions.configuration,
            )
            yield
        finally:
            starter.close()
