from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class ProtectionErrorCodes:
    UNAVAILABLE = ErrorCode(
        code=1_008_000,
        description="保护存储不可用",
        message_key="protection.unavailable",
        http_status=503,
    )
    INVALID = ErrorCode(
        code=1_008_001,
        description="保护配置或参数无效",
        message_key="protection.invalid",
        http_status=400,
    )
    CLOSED = ErrorCode(
        code=1_008_012,
        description="保护组件尚未就绪或正在关闭",
        message_key="protection.closed",
        http_status=503,
    )
    RATE_LIMITED = ErrorCode(
        code=1_008_021,
        description="请求过于频繁，请稍后重试",
        message_key="protection.rate_limited",
        http_status=429,
    )
    CAPACITY = ErrorCode(
        code=1_008_022,
        description="保护组件处理容量已满",
        message_key="protection.capacity",
        http_status=503,
    )
    LOCK_BUSY = ErrorCode(
        code=1_017_001,
        description="获取分布式锁超时",
        message_key="protection.lock_busy",
        http_status=423,
    )
    LOCK_LOST = ErrorCode(
        code=1_017_033,
        description="分布式锁租约已过期或持有者变更",
        message_key="protection.lock_lost",
        http_status=409,
    )
    DUPLICATE = ErrorCode(
        code=1_006_021,
        description="请求重复提交",
        message_key="protection.duplicate",
        http_status=409,
    )
    OWNER_LOST = ErrorCode(
        code=1_006_022,
        description="幂等状态已过期或持有者变更",
        message_key="protection.owner_lost",
        http_status=409,
    )
