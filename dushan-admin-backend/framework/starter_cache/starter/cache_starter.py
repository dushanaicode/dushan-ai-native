from collections.abc import Iterable

from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_manager import CacheManager
from framework.starter_cache.model.cache_key_container import CacheKeyContainer
from framework.starter_di.decorators.components import starter


@starter
class CacheStarter:
    """把缓存资源接入应用启动与关闭，不负责发现业务类或声明缓存键。

    先登记并校验全部 CacheKey，再建立连接：键声明错误属于部署错误，
    应该在建立任何连接之前就失败，而不是连上以后才报无效前缀。
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        cache_key_registry: CacheKeyRegistry,
        settings: CacheSettings,
    ) -> None:
        self.cache_manager = cache_manager
        self.cache_key_registry = cache_key_registry
        self.settings = settings

    async def open(self, containers: Iterable[type[CacheKeyContainer]]) -> None:
        """登记键声明并建立全部 Redis 连接。"""
        self.cache_key_registry.register(containers, self.settings)
        await self.cache_manager.open()

    async def close(self) -> None:
        """释放本应用持有的全部缓存连接。"""
        await self.cache_manager.close()

    @property
    def is_ready(self) -> bool:
        """连接是否已经完整就绪。"""
        return self.cache_manager.is_ready
