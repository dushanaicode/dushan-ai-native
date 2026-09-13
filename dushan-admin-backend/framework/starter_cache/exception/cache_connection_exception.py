from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes
from framework.starter_cache.exception.cache_exception import CacheException


class CacheConnectionException(CacheException):
    """连接建立、探活或客户端查找失败。"""

    default_error_code = CacheErrorCodes.CONNECTION_FAILED
