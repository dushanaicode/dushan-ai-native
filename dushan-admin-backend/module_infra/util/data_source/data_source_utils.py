from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.config.data_source_settings import DataSourceSettings
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.connection_factory import ConnectionFactory
from framework.starter_di.decorators.components import util
from framework.starter_di.decorators.inject import Inject


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
