from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException


class CacheLockException(CacheException):
    """分布式锁参数、获取或释放失败。"""

    default_error_code = CacheErrorCodes.LOCK_ACQUIRE_FAILED
