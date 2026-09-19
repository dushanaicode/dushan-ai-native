from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class DatabaseErrorCodes:
    """数据库错误段 1_012_000～1_012_999。"""

    ERROR = ErrorCode(code=1_012_000, description="数据库操作失败", message_key="database.error")
    NOT_READY = ErrorCode(
        code=1_012_011, description="数据库尚未就绪或正在关闭", message_key="database.not_ready"
    )
    TRANSACTION_REQUIRED = ErrorCode(
        code=1_012_012, description="操作要求活动事务", message_key="database.transaction_required"
    )
    OPERATION_FORBIDDEN = ErrorCode(
        code=1_012_014,
        description="数据库操作不符合受管契约",
        message_key="database.operation_forbidden",
    )
    CONTEXT_MISMATCH = ErrorCode(
        code=1_012_015,
        description="数据库上下文不属于当前任务",
        message_key="database.context_mismatch",
    )
    ROLLBACK_ONLY = ErrorCode(
        code=1_012_016, description="嵌套操作失败，事务已回滚", message_key="database.rollback_only"
    )
    AFTER_COMMIT_FAILED = ErrorCode(
        code=1_012_017,
        description="数据已提交，但后续处理失败",
        message_key="database.after_commit_failed",
    )
    CONNECTION_FAILED = ErrorCode(
        code=1_012_002, description="数据库连接检查失败", message_key="database.connection_failed"
    )
    UNIQUE_VIOLATION = ErrorCode(
        code=1_012_020, description="数据库唯一约束冲突", message_key="database.unique_violation"
    )
    FOREIGN_KEY_VIOLATION = ErrorCode(
        code=1_012_021,
        description="数据库外键约束冲突",
        message_key="database.foreign_key_violation",
    )
    NOT_NULL_VIOLATION = ErrorCode(
        code=1_012_022, description="数据库必填字段缺失", message_key="database.not_null_violation"
    )
    CHECK_VIOLATION = ErrorCode(
        code=1_012_023, description="数据库检查约束冲突", message_key="database.check_violation"
    )
    INTEGRITY_VIOLATION = ErrorCode(
        code=1_012_024,
        description="数据库完整性约束冲突",
        message_key="database.integrity_violation",
    )
    PROGRAMMING_ERROR = ErrorCode(
        code=1_012_025, description="数据库语句或编程错误", message_key="database.programming_error"
    )
    POOL_TIMEOUT = ErrorCode(
        code=1_012_026, description="数据库连接池等待超时", message_key="database.pool_timeout"
    )
    STATEMENT_TIMEOUT = ErrorCode(
        code=1_012_027, description="数据库语句执行超时", message_key="database.statement_timeout"
    )
    DEADLOCK = ErrorCode(
        code=1_012_028, description="数据库事务发生死锁", message_key="database.deadlock"
    )
    SERIALIZATION_FAILURE = ErrorCode(
        code=1_012_029,
        description="数据库事务序列化冲突",
        message_key="database.serialization_failure",
    )
    STATEMENT_CANCELLED = ErrorCode(
        code=1_012_030, description="数据库语句已取消", message_key="database.statement_cancelled"
    )
    DATA_ERROR = ErrorCode(
        code=1_012_031, description="数据库字段数据无效", message_key="database.data_error"
    )
