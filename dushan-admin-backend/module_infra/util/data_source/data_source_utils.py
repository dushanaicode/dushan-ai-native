from framework.common.utils import CleanupUtils
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

    async def test_connection(self, config):
        source = DataSourceSettings(
            name="connection_test", url=config.url, role="named", weight=100, pool=None, tls=None
        )
        engine = ConnectionFactory.create(source, self.settings)
        try:
            await ConnectionFactory.probe(engine)
            return True, "连接成功"
        except Exception as error:
            return False, "连接失败: " + type(error).__name__
        finally:
            error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                engine.dispose, "测试数据源关闭"
            )
            CleanupUtils.raise_collected_cleanup_errors(
                "测试数据源关闭失败",
                [] if error is None else [error],
                caller_cancellation=cancellation,
            )
