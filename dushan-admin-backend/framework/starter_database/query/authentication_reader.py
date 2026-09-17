from framework.common.utils.asyncio.cleanup_utils import CleanupUtils
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.query.authentication_condition_builder import (
    AuthenticationConditionBuilder,
)
from framework.starter_database.query.authentication_model_registry import (
    AuthenticationModelRegistry,
)


class AuthenticationReader:
    """给认证仓储绑定有限模型和服务器租户，只返回主库查询值。

    不交付 Session/Connection，不修改普通查询策略，也不建立可向后泄漏的豁免帧。
    业务在构造时显式列出认证所需模型；客户端不能控制白名单或目标租户。
    """

    def __init__(self, database, models, *, tenant_id):
        if not isinstance(tenant_id, str) or not tenant_id:
            raise ValueError("认证读取必须由服务器指定租户")
        self.database = database
        self.builder = AuthenticationConditionBuilder(
            AuthenticationModelRegistry(models), tenant_id
        )

    async def read(self, statement):
        """校验并过滤所有主表、别名与子查询；结果已缓冲，连接在返回前关闭。"""
        statement = self.builder.select(statement, orm=False)
        transactions = self.database._transactions
        with transactions._operation_scope(), DatabaseErrorTranslator.boundary():
            entry = transactions.registry.acquire(readonly=False)
            connection = None
            try:
                connection = await entry.engine.connect()
                result = await connection.execute(statement)
                return result.mappings().all()
            finally:
                try:
                    if connection is not None:
                        error, cancellation = await CleanupUtils.run_cancellation_safe_cleanup(
                            connection.close, "认证主库连接关闭"
                        )
                        CleanupUtils.raise_collected_cleanup_errors(
                            "认证连接关闭失败",
                            [] if error is None else [error],
                            caller_cancellation=cancellation,
                        )
                finally:
                    entry.release()
