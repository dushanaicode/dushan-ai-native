from framework.starter_di.public import (
    Inject,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityRealm,
)
from framework.starter_web.public import (
    RoutePolicy,
)
from framework.starter_websocket.public import (
    HandlerDefinition,
    socket_handler,
)
from module_infra.framework.websocket.handler.system_message_handler_base import (
    SystemMessageHandlerBase,
)
from module_infra.framework.websocket.handler.user_info_resp_vo import UserInfoRespVO
from module_infra.framework.websocket.infra_socket_request import InfraSocketRequest
from module_system.api.user.admin_user_api import AdminUserApi


@socket_handler(
    HandlerDefinition(
        audience="infra",
        type="get-user-info",
        payload=InfraSocketRequest,
        policy=RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
    )
)
class UserInfoMessageHandler(SystemMessageHandlerBase):
    service: AdminUserApi = Inject()
    security: SecurityContext = Inject()
    response_type = "get-user-info-response"

    async def process_message(self):
        """读取当前用户并按消息响应模型输出。"""
        user = await self.service.get_user(int(self.security.require().account_id))
        return UserInfoRespVO.model_validate(user).to_response()
