from redis.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusyLoadingError,
    MasterDownError,
    ReadOnlyError,
    ResponseError,
)
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    TimeoutError as RedisTimeoutError,
)


class RedisRecovery:
    """只重试暂时连接故障及清理后缺失的消费组，不吞权限和数据格式错误。"""

    @classmethod
    def retryable(cls, error: Exception) -> bool:
        if isinstance(error, ExceptionGroup):
            return all(cls.retryable(item) for item in error.exceptions)
        current = error
        recoverable = False
        while current is not None:
            # 认证异常继承 ConnectionError；检查完整原因链，避免连接包装掩盖凭据错误。
            if isinstance(current, (AuthenticationError, AuthorizationError)):
                return False
            if isinstance(current, ExceptionGroup):
                if not cls.retryable(current):
                    return False
                recoverable = True
            if isinstance(
                current,
                (
                    ConnectionError,
                    TimeoutError,
                    RedisConnectionError,
                    RedisTimeoutError,
                    BusyLoadingError,
                    MasterDownError,
                    ReadOnlyError,
                ),
            ):
                recoverable = True
            if isinstance(current, ResponseError) and str(current).startswith("NOGROUP "):
                recoverable = True
            current = current.__cause__
        return recoverable
