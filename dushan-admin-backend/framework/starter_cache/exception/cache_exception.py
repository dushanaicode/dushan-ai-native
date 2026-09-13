from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes


class CacheException(ServerException):
    """缓存操作失败的公共基类；保留原始 Redis 异常作为 cause，不吞掉失败原因。

    默认可重试，表示同一请求重放通常安全；序列化失败等确定性错误在子类关闭该标记。
    """

    default_error_code = CacheErrorCodes.ERROR
    log_level = LogLevelEnum.ERROR
    retryable = True
