from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_di.public import (
    Inject,
    util,
)


@util
class CacheKeyUtils:
    registry: CacheKeyRegistry = Inject()

    def build_scan_patterns(self, cache_name):
        return [CacheKeyResolver.build_prefix_pattern(self.registry.get_all()[cache_name])]

    def generate_keys(self, cache_name, identifier):
        return [CacheKeyResolver.build_full_key(self.registry.get_all()[cache_name], identifier)]
