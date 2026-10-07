from framework.starter_database.public import (
    ConnectionFactory,
    DatabaseSettings,
    DataSourceSettings,
)
from framework.starter_di.public import (
    Inject,
    util,
)


@util
class DataSourceUtils:
    settings: DatabaseSettings = Inject()

    async def test_connection(self, config) -> None:
        """探测临时数据源；保留技术异常，由服务层决定业务结果。"""
        source = DataSourceSettings(
            name="connection_test",
            url=config.url,
            role="named",
            weight=100,
            pool=None,
            tls=None,
        )
        async with ConnectionFactory.temporary_engine(source, self.settings) as engine:
            await ConnectionFactory.probe(engine)
