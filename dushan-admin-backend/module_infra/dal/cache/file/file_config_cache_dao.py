from framework.starter_cache.repository.base_cache_dao import BaseCacheDAO
from framework.starter_di.decorators.components import dao
from module_infra.dal.cache.cache_key_constants import InfraCacheKeys


@dao
class FileConfigCacheDAO(BaseCacheDAO):
    def __init__(self):
        super().__init__(InfraCacheKeys.FILE_CONFIG_CACHE)

    async def get_config(self, config_id):
        return await self.get(str(config_id))

    async def set_config(self, config_id, config_info, ttl):
        await self.set(str(config_id), config_info, ttl_seconds=ttl)

    async def delete_config(self, config_id):
        return await self.delete(str(config_id))

    async def get_or_load_config(self, config_id, loader, ttl):
        return await self.get_or_load(str(config_id), loader, ttl_seconds=ttl)
