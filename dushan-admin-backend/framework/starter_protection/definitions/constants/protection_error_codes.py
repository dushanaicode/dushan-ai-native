from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class ProtectionErrorCodes:
    """保护组件错误段 1_008_000～1_008_999。

    限流、分布式锁与幂等在 Native 合并为同一个 starter，统一使用本段；
    不保留旧项目按子组件拆分的 1_006 与 1_017 编号。
    """

    UNAVAILABLE = ErrorCode(
        code=1_008_000,
        description="保护存储不可用",
        message_key="protection.unavailable",
    )
    INVALID = ErrorCode(
        code=1_008_001,
        description="保护配置或参数无效",
        message_key="protection.invalid",
    )
    CLOSED = ErrorCode(
        code=1_008_012,
        description="保护组件尚未就绪或正在关闭",
        message_key="protection.closed",
    )
    RATE_LIMITED = ErrorCode(
        code=1_008_021,
        description="请求过于频繁，请稍后重试",
        message_key="protection.rate_limited",
    )
    CAPACITY = ErrorCode(
        code=1_008_022,
        description="保护组件处理容量已满",
        message_key="protection.capacity",
    )
    LOCK_BUSY = ErrorCode(
        code=1_008_031,
        description="获取分布式锁超时",
        message_key="protection.lock_busy",
    )
    LOCK_LOST = ErrorCode(
        code=1_008_032,
        description="分布式锁租约已过期或持有者变更",
        message_key="protection.lock_lost",
    )
    DUPLICATE = ErrorCode(
        code=1_008_041,
        description="请求重复提交",
        message_key="protection.duplicate",
    )
    OWNER_LOST = ErrorCode(
        code=1_008_042,
        description="幂等状态已过期或持有者变更",
        message_key="protection.owner_lost",
    )
