from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.starter_cache.exception.cache_error_codes import CacheErrorCodes


class CacheConfigException(ConfigurationException):
    """缓存声明或配置不合法；属于部署期错误，重放请求不会恢复。"""

    default_error_code = CacheErrorCodes.CONFIG_ERROR
