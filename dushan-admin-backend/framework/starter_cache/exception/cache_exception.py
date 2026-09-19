from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_cache.definitions.constants.cache_error_codes import CacheErrorCodes


class CacheException(ServerException):
    """缓存组件的唯一异常；失败原因由 CacheErrorCodes 区分，保留原始 Redis 异常作为 cause。

    默认可重试，表示同一请求重放通常安全；序列化与配置类错误由本异常关闭该标记。
    """

    default_error_code = CacheErrorCodes.ERROR
    log_level = LogLevelEnum.ERROR

    @property
    def retryable(self) -> bool:
        """确定性的数据与配置错误重放不会恢复。"""
        return self.error_code.code not in {
            CacheErrorCodes.SERIALIZATION_FAILED.code,
            CacheErrorCodes.DESERIALIZATION_FAILED.code,
            CacheErrorCodes.CONFIG_ERROR.code,
            CacheErrorCodes.INVALID_CACHE_KEY.code,
        }
