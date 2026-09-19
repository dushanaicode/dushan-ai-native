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
from module_infra.controller.admin.websocket.vo.websocket_broadcast_req_vo import (
    WebsocketBroadcastReqVO,
)
from module_infra.controller.admin.websocket.vo.websocket_send_to_user_req_vo import (
    WebsocketSendToUserReqVO,
)
from module_infra.service.websocket.websocket_service import WebSocketService

websocket_controller_router = APIRouter(prefix="/websocket")


class WebsocketController:
    @staticmethod
    @websocket_controller_router.get("/status")
    @RoutePolicy(
        permissions=("infra:websocket:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_websocket_status(
        service: WebSocketService = Depends(DiDependency(WebSocketService)),
    ):
        return Result.success(await service.get_status_info())

    @staticmethod
    @websocket_controller_router.post("/broadcast")
    @RoutePolicy(
        permissions=("infra:websocket:send",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def broadcast(
        request: WebsocketBroadcastReqVO,
        service: WebSocketService = Depends(DiDependency(WebSocketService)),
    ):
        await service.broadcast_object_message(request.message)
        return Result.success(True)

    @staticmethod
    @websocket_controller_router.post("/send-to-user")
    @RoutePolicy(
        permissions=("infra:websocket:send",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def send_to_user(
        request: WebsocketSendToUserReqVO,
        service: WebSocketService = Depends(DiDependency(WebSocketService)),
    ):
        await service.send_to_user(request.user_type, request.user_id, request.message)
        return Result.success(True)
