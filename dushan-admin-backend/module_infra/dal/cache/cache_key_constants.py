from framework.starter_cache.enums.cache_namespace import CacheNamespace
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_di.decorators.components import framework


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
