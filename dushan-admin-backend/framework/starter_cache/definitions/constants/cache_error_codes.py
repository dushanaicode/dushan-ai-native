from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class CacheErrorCodes:
    """缓存错误段 1_001_000～1_001_999。

    仅定义稳定编号和展示文案；重试策略由 CacheException 负责。
    """

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

    # 序列化失败对同一份数据重放仍会失败，因此不可重试。
    SERIALIZATION_FAILED = ErrorCode(
        code=1_001_011,
        description="缓存对象序列化失败",
        message_key="cache.serialization_failed",
    )
    DESERIALIZATION_FAILED = ErrorCode(
        code=1_001_012,
        description="缓存数据反序列化失败",
        message_key="cache.deserialization_failed",
    )

    # 声明与配置问题属于部署期错误，重放请求不会恢复。
    CONFIG_ERROR = ErrorCode(
        code=1_001_021,
        description="缓存配置错误",
        message_key="cache.config_error",
    )
    INVALID_CACHE_KEY = ErrorCode(
        code=1_001_022,
        description="缓存键声明无效",
        message_key="cache.invalid_cache_key",
    )

    LOCK_ACQUIRE_FAILED = ErrorCode(
        code=1_001_031, description="无法获取分布式锁", message_key="cache.lock_acquire_failed"
    )
    LOCK_RELEASE_FAILED = ErrorCode(
        code=1_001_032, description="释放分布式锁失败", message_key="cache.lock_release_failed"
    )
    # 等待上界内锁仍被其他持有者占用；这是正常竞争结果，调用方可以退避后重试。
    LOCK_CONTENDED = ErrorCode(
        code=1_001_033, description="分布式锁竞争未获取", message_key="cache.lock_contended"
    )

    OPERATION_FAILED = ErrorCode(
        code=1_001_041, description="缓存操作失败", message_key="cache.operation_failed"
    )
