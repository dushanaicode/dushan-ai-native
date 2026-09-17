from loguru import logger

from framework.starter_di.decorators.components import starter
from framework.starter_protection.core.protection_service import ProtectionService
from framework.starter_protection.integration.monitor_protection_observer import (
    MonitorProtectionObserver,
)


@starter
class ProtectionStarter:
    """为限流、锁和幂等接入观测提供器，统一管理保护资源启停。"""

    def __init__(self, service: ProtectionService):
        self.service = service

    async def open(self, *, monitor=None):
        observer = None
        if (
            self.service.settings.tracing_enabled
            and monitor is not None
            and monitor.settings.enabled
        ):
            observer = MonitorProtectionObserver(monitor)
            logger.debug("【ProtectionStarter 】已接入保护操作追踪")
        await self.service.open(observer=observer)

    async def close(self):
        await self.service.close()
        if self.service.settings.enabled:
            logger.info("【ProtectionStarter 】保护资源已关闭")
