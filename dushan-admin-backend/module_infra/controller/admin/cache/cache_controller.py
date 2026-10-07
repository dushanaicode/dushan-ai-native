from fastapi import APIRouter, Depends

from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.cache.vo.monitor.monitor_resp_vo import MonitorRespVO
from module_infra.service.cache.cache_service import CacheService

cache_controller = APIRouter(prefix="/cache", tags=["Infra - 缓存管理"])


class CacheController:
    @staticmethod
    @cache_controller.get("/get-monitor-info", summary="获得缓存监控信息")
    @RoutePolicy(
        permissions=("infra:cache:get-monitor-info",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_cache_monitor_info(
        cache_service: CacheService = Depends(DiDependency(CacheService)),
    ) -> Result[MonitorRespVO]:
        result_obj: MonitorRespVO = await cache_service.get_cache_monitor_info()
        return Result.success(data=result_obj)
