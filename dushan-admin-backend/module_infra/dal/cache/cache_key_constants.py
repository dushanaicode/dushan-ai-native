from framework.starter_cache.public import CacheKey, CacheKeyContainer, CacheNamespace
from framework.starter_di.public import (
    framework,
)


@framework(providers=[CacheKeyContainer])
class InfraCacheKeys(CacheKeyContainer):
    MONITOR_REDIS_INFO = CacheKey(
        key="infra:monitor_redis_info",
        remark="Redis 监控",
        client_name="default",
        namespace=CacheNamespace.GLOBAL,
        default_ttl_seconds=10,
    )
    FILE_CONFIG_CACHE = CacheKey(
        key="infra:file_config_cache",
        remark="文件配置",
        client_name="default",
        namespace=CacheNamespace.TENANT,
        default_ttl_seconds=300,
    )
