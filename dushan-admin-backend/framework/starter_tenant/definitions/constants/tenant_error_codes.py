from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class TenantErrorCodes:
    """租户错误段 1_005_000～1_005_999。"""

    MISSING = ErrorCode(
        code=1_005_001,
        description="缺少有效租户上下文",
        message_key="tenant.missing",
    )
    UNKNOWN = ErrorCode(code=1_005_002, description="租户不存在", message_key="tenant.unknown")
    DISABLED = ErrorCode(code=1_005_003, description="租户不可用", message_key="tenant.disabled")
    DENIED = ErrorCode(
        code=1_005_004,
        description="租户访问未获授权",
        message_key="tenant.denied",
    )
    CONFIGURATION = ErrorCode(
        code=1_005_005,
        description="租户资源或提供者未就绪",
        message_key="tenant.configuration",
    )
    MODE = ErrorCode(
        code=1_005_006,
        description="租户部署模式与封存记录不一致，请通过独立部署入口切换",
        message_key="tenant.mode",
    )
    MODEL = ErrorCode(
        code=1_005_007,
        description="模型租户归属、唯一键或关联约束无效",
        message_key="tenant.model",
    )
    WRITE = ErrorCode(code=1_005_008, description="写入违反租户归属", message_key="tenant.write")
    EXPIRED = ErrorCode(
        code=1_005_009,
        description="租户执行授权已失效",
        message_key="tenant.expired",
    )
    CLOSED = ErrorCode(
        code=1_005_010,
        description="租户运行时已关闭",
        message_key="tenant.closed",
    )
