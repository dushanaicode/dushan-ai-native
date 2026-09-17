from fastapi import APIRouter, Depends, Query

from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_infra.controller.admin.cache.vo.cache.cache_clear_cache_by_key_req_vo import (
    ClearCacheByKeyReqVO,
)
from module_infra.controller.admin.cache.vo.cache.cache_clear_cache_by_name_req_vo import (
    ClearCacheByNameReqVO,
)
from module_infra.controller.admin.cache.vo.cache.cache_db_info_resp_vo import CacheDbInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_delete_key_req_vo import DeleteKeyReqVO
from module_infra.controller.admin.cache.vo.cache.cache_info_resp_vo import CacheInfoRespVO
from module_infra.controller.admin.cache.vo.cache.cache_key_detail_req_vo import KeyDetailReqVO
from module_infra.controller.admin.cache.vo.cache.cache_key_detail_resp_vo import (
    CacheKeyDetailRespVO,
)
from module_infra.controller.admin.cache.vo.cache.cache_keys_req_vo import CacheKeysReqVO
from module_infra.controller.admin.cache.vo.cache.cache_scan_db_keys_req_vo import ScanDbKeysReqVO
from module_infra.controller.admin.cache.vo.cache.cache_value_req_vo import CacheValueReqVO
from module_infra.service.cache.cache_service import CacheService

cache_monitor_controller = APIRouter(prefix="/cache/monitor", tags=["Infra - 缓存监控"])


class CacheMonitorController:
    @staticmethod
    @cache_monitor_controller.get("/get-names", summary="获得所有缓存名称")
    @RoutePolicy(
        permissions=("infra:cache:get-names",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_cache_names(
        page_param: PageQuery = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[PageResult[CacheInfoRespVO]]:
        result: PageResult[CacheInfoRespVO] = await cache_service.get_cache_names(page_param)
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.get("/get-keys", summary="获得指定缓存名称下的键列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_cache_keys(
        req_vo: CacheKeysReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[PageResult[str]]:
        result: PageResult[str] = await cache_service.get_cache_keys(req_vo.key_prefix, req_vo)
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.get("/get-value", summary="获得指定缓存键的值")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_cache_value(
        req_vo: CacheValueReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[CacheInfoRespVO]:
        result: CacheInfoRespVO | None = await cache_service.get_cache_value(
            req_vo.key_prefix, req_vo.cache_key
        )
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.delete("/clear-cache-name", summary="清除指定缓存名称下的所有缓存")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def clear_cache_by_name(
        req_vo: ClearCacheByNameReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[bool]:
        await cache_service.clear_cache_by_name(req_vo.key_prefix)
        return Result.success(data=True)

    @staticmethod
    @cache_monitor_controller.delete("/clear-cache-key", summary="清除匹配模式的缓存键")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def clear_cache_by_key(
        req_vo: ClearCacheByKeyReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[bool]:
        await cache_service.clear_cache_by_key(req_vo.cache_key_pattern)
        return Result.success(data=True)

    @staticmethod
    @cache_monitor_controller.delete("/clear-cache-all", summary="清除所有缓存(FLUSHDB)")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def clear_all_caches(
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[bool]:
        await cache_service.clear_all_caches()
        return Result.success(data=True)

    @staticmethod
    @cache_monitor_controller.get("/db-list", summary="获取所有配置的 Redis DB 列表")
    @RoutePolicy(
        permissions=("infra:cache:get-names",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_db_list(
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[list[CacheDbInfoRespVO]]:
        result = await cache_service.get_db_list()
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.get("/db-keys", summary="扫描指定 DB 中的所有 key")
    @RoutePolicy(
        permissions=("infra:cache:get-names",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def scan_db_keys(
        req_vo: ScanDbKeysReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[list[str]]:
        result = await cache_service.scan_db_keys(req_vo.db_name, req_vo.pattern)
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.get("/key-detail", summary="获取指定 key 的详细信息")
    @RoutePolicy(
        permissions=("infra:cache:get-names",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_key_detail(
        req_vo: KeyDetailReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[CacheKeyDetailRespVO]:
        result = await cache_service.get_key_detail(req_vo.db_name, req_vo.key)
        return Result.success(data=result)

    @staticmethod
    @cache_monitor_controller.delete("/delete-key", summary="删除指定 DB 中的单个 key")
    @RoutePolicy(
        permissions=("infra:cache:get-names",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_key(
        req_vo: DeleteKeyReqVO = Query(),
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[bool]:
        result = await cache_service.delete_key(req_vo.db_name, req_vo.key)
        return Result.success(data=result)
