from typing import Any

from fastapi import APIRouter, Depends

from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
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
    ) -> Result[dict[str, Any]]:
        result_obj: MonitorRespVO = await cache_service.get_cache_monitor_info()
        result_dict = result_obj.model_dump(mode="json")
        return Result.success(data=result_dict)
