from framework.starter_cache.model.cache_entry_invalidation_command import (
    CacheEntryInvalidationCommand,
)
from framework.starter_cache.model.cache_prefix_invalidation_command import (
    CachePrefixInvalidationCommand,
)

# 失效调度器接受的全部命令类型；新增命令必须同时在调度器补上分支。
type CacheInvalidationCommand = CacheEntryInvalidationCommand | CachePrefixInvalidationCommand
