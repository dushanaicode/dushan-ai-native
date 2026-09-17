from fastapi import APIRouter, Depends

from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_infra.controller.admin.server.vo.server_resp_vo import ServerMonitorRespVO
from module_infra.service.server.server_service import ServerService

server_controller = APIRouter(prefix="/server", tags=["Infra - 服务器信息管理"])


class ServerController:
    @staticmethod
    @server_controller.get("/list", summary="获取服务器信息")
    @RoutePolicy(
        permissions=("infra:server:list",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_swagger_list(
        server_service: ServerService = Depends(DiDependency(ServerService)),
    ) -> Result[ServerMonitorRespVO]:
        result_obj: ServerMonitorRespVO = await server_service.get_server_list()
        return Result.success(data=result_obj)
