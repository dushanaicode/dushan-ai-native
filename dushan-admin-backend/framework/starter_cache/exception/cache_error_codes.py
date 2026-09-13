from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class CacheErrorCodes:
    """缓存错误段 1_001_000～1_001_999。"""

    ERROR = ErrorCode(code=1_001_000, description="缓存模块异常", message_key="cache.error")
    NOT_INITIALIZED = ErrorCode(
        code=1_001_001, description="缓存尚未就绪或正在关闭", message_key="cache.not_initialized"
    )
    INIT_FAILED = ErrorCode(
        code=1_001_002, description="缓存初始化失败", message_key="cache.init_failed"
    )
    CLIENT_NOT_FOUND = ErrorCode(
        code=1_001_003, description="无法获取缓存客户端", message_key="cache.client_not_found"
    )
    CONNECTION_FAILED = ErrorCode(
        code=1_001_004, description="缓存连接失败", message_key="cache.connection_failed"
    )
    SERIALIZATION_FAILED = ErrorCode(
        code=1_001_011, description="缓存对象序列化失败", message_key="cache.serialization_failed"
    )
    DESERIALIZATION_FAILED = ErrorCode(
        code=1_001_012,
        description="缓存数据反序列化失败",
        message_key="cache.deserialization_failed",
    )
    CONFIG_ERROR = ErrorCode(
        code=1_001_021, description="缓存配置错误", message_key="cache.config_error"
    )
    INVALID_CACHE_KEY = ErrorCode(
        code=1_001_022, description="缓存键声明无效", message_key="cache.invalid_cache_key"
    )
    LOCK_ACQUIRE_FAILED = ErrorCode(
        code=1_001_031, description="无法获取分布式锁", message_key="cache.lock_acquire_failed"
    )
    LOCK_RELEASE_FAILED = ErrorCode(
        code=1_001_032, description="释放分布式锁失败", message_key="cache.lock_release_failed"
    )
    OPERATION_FAILED = ErrorCode(
        code=1_001_041, description="缓存操作失败", message_key="cache.operation_failed"
    )
