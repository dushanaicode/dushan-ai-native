from framework.starter_database.session.managed_session import ManagedSession
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.inject import Inject


class BaseAggregateMapper:
    """跨表聚合的显式只读入口，复用已有事务及当前应用的数据源路由。"""

    session_provider: SessionProvider = Inject()

    def _get_read_session(self):
        return self.session_provider.read_session()

    async def read(self, statement):
        ManagedSession.validate_statement(statement, readonly=True)
        async with self._get_read_session() as session:
            return await session.execute(statement)
