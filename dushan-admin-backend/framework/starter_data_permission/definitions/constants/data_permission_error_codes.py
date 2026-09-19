from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class DataPermissionErrorCodes:
    """数据权限错误段 1_006_000～1_006_999。"""

    MISSING = ErrorCode(
        code=1_006_001,
        description="数据权限主体不可用",
        message_key="data_permission.missing",
    )
    DENIED = ErrorCode(
        code=1_006_002,
        description="数据范围拒绝访问",
        message_key="data_permission.denied",
    )
    STALE = ErrorCode(
        code=1_006_003,
        description="数据权限快照已失效",
        message_key="data_permission.stale",
    )
    CONFIGURATION = ErrorCode(
        code=1_006_004,
        description="数据权限配置无效",
        message_key="data_permission.configuration",
    )
    PROVIDER = ErrorCode(
        code=1_006_005,
        description="数据权限提供者不可用",
        message_key="data_permission.provider",
    )
    UNREGISTERED = ErrorCode(
        code=1_006_006,
        description="模型未声明数据访问策略",
        message_key="data_permission.unregistered",
    )
    WRITE = ErrorCode(
        code=1_006_007,
        description="写入包含未授权记录或归属字段",
        message_key="data_permission.write",
    )
    CLOSED = ErrorCode(
        code=1_006_008,
        description="数据权限服务已关闭",
        message_key="data_permission.closed",
    )
