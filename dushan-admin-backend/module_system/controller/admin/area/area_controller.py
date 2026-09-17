from fastapi import APIRouter, Depends, Query

from framework.common.exception.exceptions.service_exception import ServiceException
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_ip.model.area import Area
from framework.starter_ip.service.area_service import AreaService
from framework.starter_ip.service.ip_location_service import IpLocationService
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.area.vo.area_node_resp_vo import AreaNodeRespVO
from module_system.controller.admin.area.vo.ip_req_vo import IpReqVO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants

area_controller = APIRouter(prefix="/area", tags=["System - 地区管理"])


class AreaController:
    @staticmethod
    @area_controller.get("/tree", summary="获得地区树")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_area_tree(
        area_service: AreaService = Depends(DiDependency(AreaService)),
    ) -> Result[list[AreaNodeRespVO]]:
        area = area_service.get_area(Area.ID_CHINA)
        if not area:
            raise ServiceException(ErrorCodeConstants.IP_AREA_NOT_FOUND)
        vo_list = [
            AreaNodeRespVO.model_validate(area_service.convert_to_dict(child))
            for child in area.children
        ]
        return Result.success(data=vo_list)

    @staticmethod
    @area_controller.get("/get-by-ip", summary="获得 IP 对应的地区名")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_area_by_ip(
        req_vo: IpReqVO = Query(),
        ip_location_service: IpLocationService = Depends(DiDependency(IpLocationService)),
    ) -> Result[str]:
        location = None
        if req_vo.ip:
            location = await ip_location_service.get_ip_location(req_vo.ip)
        return Result.success(data=location if location else "未知")
