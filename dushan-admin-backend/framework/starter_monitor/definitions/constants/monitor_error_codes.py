from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class MonitorErrorCodes:
    INIT_FAILED = ErrorCode(
        code=1_015_001,
        description="追踪资源初始化失败",
        message_key="monitor.init_failed",
    )
    INVALID_CONFIG = ErrorCode(
        code=1_015_003,
        description="追踪配置无效",
        message_key="monitor.invalid_config",
    )
    SHUTDOWN_FAILED = ErrorCode(
        code=1_015_021,
        description="追踪资源关闭失败",
        message_key="monitor.shutdown_failed",
    )
