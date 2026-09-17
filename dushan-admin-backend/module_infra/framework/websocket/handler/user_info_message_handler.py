from framework.common.utils.str.str_utils import StrUtils
from framework.starter_di.decorators.inject import Inject
from framework.starter_security.context.security_context import SecurityContext
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_websocket.decorators.socket_handler import socket_handler
from framework.starter_websocket.model.handler_definition import HandlerDefinition
from module_infra.framework.websocket.handler.system_message_handler_base import (
    SystemMessageHandlerBase,
)
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
        user = await self.service.get_user(int(self.security.require().account_id))
        values = user.model_dump(mode="json", by_alias=False)
        values["id"] = str(user.id)
        values["dept_id"] = None if user.dept_id is None else str(user.dept_id)
        values["post_ids"] = [str(identifier) for identifier in user.post_ids]
        return StrUtils.deep_transform_keys(values, StrUtils.to_camel_case)
