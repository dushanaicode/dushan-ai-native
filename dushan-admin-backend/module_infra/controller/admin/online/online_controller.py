from fastapi import APIRouter, Depends, Query, Request

from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_result import PageResult
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_infra.controller.admin.online.vo.online_force_logout_req_vo import (
    OnlineForceLogoutReqVO,
)
from module_infra.controller.admin.online.vo.online_info_req_vo import OnlineInfoReqVO
from module_infra.controller.admin.online.vo.online_resp_vo import OnlineInfoRespVO
from module_infra.service.online.online_service import OnlineService

online_controller = APIRouter(prefix="/online", tags=["Infra - 在线用户管理"])


class OnlineController:
    @staticmethod
    @online_controller.get("/list", summary="获取在线用户列表")
    @RoutePolicy(
        permissions=("infra:online:list",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_monitor_online_list(
        request: Request,
        online_service: OnlineService = Depends(DiDependency(OnlineService)),
        paginator: DataPaginator = Depends(DiDependency(DataPaginator)),
    ) -> Result[PageResult[OnlineInfoRespVO]]:
        page_req_vo = OnlineInfoReqVO.model_validate(request.query_params)
        online_users = await online_service.get_online_list(page_req_vo)
        return Result.success(paginator.paginate_list(online_users, page_req_vo))

    @staticmethod
    @online_controller.delete("/force-logout", summary="强制退出在线用户")
    @RoutePolicy(
        permissions=("infra:online:force-logout",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_monitor_online(
        req_vo: OnlineForceLogoutReqVO = Query(),
        online_service: OnlineService = Depends(DiDependency(OnlineService)),
    ) -> Result[bool]:
        await online_service.force_logout(req_vo.token_id)
        return Result.success(data=True)
