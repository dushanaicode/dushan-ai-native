from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageQuery, PageResult
from module_infra.controller.admin.cache.vo.cache.cache_db_info_resp_vo import CacheDbInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_info_resp_vo import CacheInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_key_detail_resp_vo import (
    CacheKeyDetailRespVO,
)
from module_infra.controller.admin.cache.vo.monitor.monitor_resp_vo import MonitorRespVO


@runtime_checkable
class CacheService(Protocol):
    """缓存管理服务接口"""

    async def get_cache_monitor_info(self) -> MonitorRespVO:
        """获取缓存监控的统计信息"""
        ...

    async def get_cache_names(
        self, page_param: PageQuery | None = None
    ) -> PageResult[CacheInfoRespVO]:
        """获取所有预定义的缓存名称列表"""
        ...

    async def get_cache_keys(
        self, cache_name: str, page_param: PageQuery | None = None
    ) -> PageResult[str]:
        """获取指定缓存名称下的所有键名"""
        ...

    async def get_cache_value(self, cache_name: str, cache_key: str) -> CacheInfoRespVO | None:
        """获取指定缓存名称和键名对应的缓存值"""
        ...

    async def clear_cache_by_name(self, cache_name: str) -> None:
        """清除指定缓存名称下的所有缓存项"""
        ...

    async def clear_cache_by_key(self, cache_key_pattern: str) -> None:
        """清除匹配指定模式的缓存键"""
        ...

    async def clear_all_caches(self) -> None:
        """清除当前数据库中的所有缓存"""
        ...

    async def get_db_list(self) -> list[CacheDbInfoRespVO]:
        """获取所有配置的 Redis DB 列表"""
        ...

    async def scan_db_keys(self, db_name: str, pattern: str = "*") -> list[str]:
        """扫描指定 DB 中的所有 key"""
        ...

    async def get_key_detail(self, db_name: str, key: str) -> CacheKeyDetailRespVO | None:
        """获取指定 key 的详细信息"""
        ...

    async def delete_key(self, db_name: str, key: str) -> bool:
        """删除指定 DB 中的单个 key"""
        ...
