from framework.starter_database.definitions.constants.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException


class AfterCommitException(DatabaseException):
    """事务已经提交，后续资源清理或动作失败；调用方不能按已回滚重试写入。"""

    default_error_code = DatabaseErrorCodes.AFTER_COMMIT_FAILED
    committed = True
