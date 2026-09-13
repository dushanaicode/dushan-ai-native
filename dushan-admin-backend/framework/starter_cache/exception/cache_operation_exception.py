from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException


class CacheOperationException(CacheException):
    """Redis 命令执行失败或返回值不符合协议约定。"""

    default_error_code = CacheErrorCodes.OPERATION_FAILED
