from pydantic import ConfigDict

from framework.common.schemas.base_bo import BaseBO
from framework.starter_cache.model.cache_key import CacheKey


class BaseCacheInvalidationCommand(BaseBO):
    """缓存失效命令的公共作用域：要失效哪一段前缀。

    命令在业务方法内构造，可以随事务提交后再执行，因此不持有客户端或连接。
    """

    model_config = ConfigDict(frozen=True)

    cache_key: CacheKey
