from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class JobErrorCodes:
    """任务调度错误段 1_009_000～1_009_999。"""

    ERROR = ErrorCode(code=1_009_000, description="任务调度异常", message_key="job.error")
    CONFIGURATION = ErrorCode(
        code=1_009_001,
        description="任务调度配置或 SPI 未就绪",
        message_key="job.configuration",
    )
    OWNER = ErrorCode(
        code=1_009_002,
        description="当前进程未持有调度租约",
        message_key="job.owner",
    )
    CLOSED = ErrorCode(code=1_009_003, description="任务运行时已关闭", message_key="job.closed")

    HANDLER = ErrorCode(
        code=1_009_011,
        description="任务处理器不存在或重复",
        message_key="job.handler",
    )
    PARAMETERS = ErrorCode(code=1_009_012, description="任务参数无效", message_key="job.parameters")
    CRON = ErrorCode(
        code=1_009_013,
        description="Cron 必须为有效标准五段表达式",
        message_key="job.cron",
    )
    DISABLED = ErrorCode(
        code=1_009_014,
        description="任务不存在或已停用",
        message_key="job.disabled",
    )
    CAPACITY = ErrorCode(
        code=1_009_015,
        description="任务执行请求队列已满",
        message_key="job.capacity",
    )
    SNAPSHOT = ErrorCode(
        code=1_009_016,
        description="任务定义已变化，旧请求跳过",
        message_key="job.snapshot",
    )
