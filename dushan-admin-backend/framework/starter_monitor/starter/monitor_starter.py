from contextlib import ExitStack

from loguru import logger

from framework.starter_di.decorators.components import starter
from framework.starter_monitor.core.monitor_service import MonitorService
from framework.starter_monitor.integration.monitor_query_observer import MonitorQueryObserver


@starter
class MonitorStarter:
    """启动追踪资源并接入数据库查询观测，关闭时先撤销自己拥有的绑定。"""

    def __init__(self, service: MonitorService):
        self.service = service
        self._bindings = ExitStack()

    async def open(self, *, diagnostic_logger, database=None):
        await self.service.open(diagnostic_logger=diagnostic_logger)
        if self.service.settings.enabled and database is not None:
            self.service.database = database
            if self.service.settings.query_enabled:
                self._bindings.enter_context(
                    database.observe_queries(MonitorQueryObserver(self.service))
                )
                logger.info("【MonitorStarter 】数据库查询观测已接入")

    async def close(self):
        try:
            self._bindings.close()
        finally:
            await self.service.close()
        if self.service.settings.enabled:
            logger.info("【MonitorStarter 】追踪资源已关闭")
