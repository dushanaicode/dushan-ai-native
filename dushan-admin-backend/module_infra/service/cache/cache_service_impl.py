import asyncio

from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.starter_cache.config.cache_settings import CacheSettings
from framework.starter_cache.core.cache_handler import CacheHandler
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_infra.controller.admin.cache.vo.cache.cache_db_info_resp_vo import CacheDbInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_info_resp_vo import CacheInfoRespVO
from module_infra.convert.cache.cache_convert import CacheConvert
from module_infra.dal.cache.cache.cache_monitor_dao import CacheMonitorDAO
from module_infra.service.cache.cache_service import CacheService


@service(interface=CacheService)
class CacheServiceImpl(CacheService):
    monitor: CacheMonitorDAO = Inject()
    registry: CacheKeyRegistry = Inject()
    cache: CacheHandler = Inject()
    pages: PageSettings = Inject()
    settings: CacheSettings = Inject()

    def _key(self, name):
        key = self.registry.find(name)
        if key is None:
            raise IllegalArgumentException(msg="缓存名称未注册")
        return key

    async def get_cache_monitor_info(self):
        info, size, stats = await asyncio.gather(
            self.monitor.get_redis_info(),
            self.monitor.get_db_size(),
            self.monitor.get_command_stats(),
        )
        return CacheConvert.build_monitor_info(info, size, stats)

    async def get_cache_names(self, page_param=None):
        rows = [
            CacheInfoRespVO(cache_name=name, cache_key="", cache_value=key.remark)
            for name, key in self.registry.get_all().items()
        ]
        return DataPaginator(self.pages).paginate_list(rows, page_param)

    async def get_cache_keys(self, cache_name, page_param=None):
        key = self._key(cache_name)
        rows = await self.monitor.scan_keys(
            CacheKeyResolver.build_prefix_pattern(key), key.client_name
        )
        return DataPaginator(self.pages).paginate_list(rows, page_param)

    async def get_cache_value(self, cache_name, cache_key):
        key = self._key(cache_name)
        if not cache_key.startswith(CacheKeyResolver.build_prefix(key) + ":"):
            raise IllegalArgumentException(msg="键不属于当前缓存命名空间")
        return CacheInfoRespVO(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=await self.monitor.get_value(cache_key, key.client_name),
        )

    async def clear_cache_by_name(self, cache_name):
        await self.cache.delete_all(self._key(cache_name))

    async def clear_cache_by_key(self, cache_key_pattern):
        for client in self.settings.clients:
            await self.monitor.delete_keys([cache_key_pattern], client.name)

    async def clear_all_caches(self):
        await asyncio.gather(
            *(self.monitor.flush_db(client.name) for client in self.settings.clients)
        )

    async def get_db_list(self):
        stats = await self.monitor.get_all_client_stats()
        return [
            CacheDbInfoRespVO(
                name=client.name,
                db_index=client.db,
                label=f"{client.name} (DB {client.db})",
                key_count=stats[client.name]["dbsize"],
            )
            for client in self.settings.clients
        ]

    async def scan_db_keys(self, db_name, pattern="*"):
        return await self.monitor.scan_all_keys_in_db(db_name, pattern)

    async def get_key_detail(self, db_name, key):
        return await self.monitor.get_key_detail(db_name, key)

    async def delete_key(self, db_name, key):
        return bool(await self.monitor.delete_raw_key(db_name, key))
