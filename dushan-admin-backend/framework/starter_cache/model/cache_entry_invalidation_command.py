from typing import Annotated

from pydantic import StringConstraints

from framework.starter_cache.model.base_cache_invalidation_command import (
    BaseCacheInvalidationCommand,
)

type CacheIdentifier = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


class CacheEntryInvalidationCommand(BaseCacheInvalidationCommand):
    """失效前缀下的一个确定标识。"""

    identifier: CacheIdentifier
