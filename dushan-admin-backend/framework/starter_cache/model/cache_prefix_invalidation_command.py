from framework.starter_cache.model.base_cache_invalidation_command import (
    BaseCacheInvalidationCommand,
)


class CachePrefixInvalidationCommand(BaseCacheInvalidationCommand):
    """失效该前缀下的全部键。"""
