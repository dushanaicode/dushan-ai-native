from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class RowAccessErrorCodes:
    """行级访问策略的通用失败原因（1_012_100～1_012_199）；各策略实现映射到本域错误码。"""

    STALE = ErrorCode(code=1_012_100, description="访问快照已失效", message_key="row_access.stale")
    CONFIGURATION = ErrorCode(
        code=1_012_101,
        description="访问策略配置无效",
        message_key="row_access.configuration",
    )
    WRITE = ErrorCode(
        code=1_012_102, description="写入违反访问策略", message_key="row_access.write"
    )
