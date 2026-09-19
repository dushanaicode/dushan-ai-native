from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes


class DatabaseException(ServerException):
    """数据库失败仅保留安全分类，原始 SQL、参数和驱动异常不属于公开诊断契约。"""

    default_error_code = DatabaseErrorCodes.ERROR
    retryable = False

    def __safe_diagnostic__(self):
        """为日志和第三方追踪生成无 traceback、cause、context 引用的快照。"""
        safe = type(self)(error_code=self.error_code)
        safe.context = {
            key: value
            for key, value in self.context.items()
            if key in {"category", "sqlstate", "vendor_code", "dialect", "phase"}
        }
        safe.retryable = self.retryable
        return safe
