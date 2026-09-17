from loguru import logger

from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.di_container import DiContainer


class DiStarter:
    """在 DI 容器自身之外组装应用上下文，统一启动与失败后的关闭入口。"""

    def __init__(self):
        self.application = None

    async def open(self, components, *, configuration, settings, enabled_modules, instances):
        container = DiContainer(
            components,
            configuration=configuration,
            settings=settings,
            enabled_modules=enabled_modules,
            instances=instances,
        )
        self.application = ApplicationContext(container)
        await self.application.startup()
        logger.info("【DiStarter 】应用上下文装配完成")
        return self.application

    async def close(self):
        await self.application.shutdown()
        logger.info("【DiStarter 】应用容器已关闭")
