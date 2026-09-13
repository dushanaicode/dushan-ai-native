from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException


class CacheSerializationException(CacheException):
    """缓存值序列化或反序列化失败；同一份数据重试仍会失败，因此不可重试。"""

    default_error_code = CacheErrorCodes.SERIALIZATION_FAILED
    retryable = False
