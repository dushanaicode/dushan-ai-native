from framework.common.exception import (
    IllegalArgumentException,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_websocket.public import (
    SocketMessage,
)
from framework.starter_websocket.public import (
    WebSocketService as NativeWebSocketService,
)
from module_infra.controller.admin.websocket.vo.websocket_message_vo import WebsocketMessageVO
from module_infra.convert.websocket.websocket_convert import WebSocketConvert
from module_infra.service.websocket.websocket_service import WebSocketService
from module_infra.util.websocket.websocket_session_utils import WebSocketSessionUtils


@service(interface=WebSocketService)
class WebSocketServiceImpl(WebSocketService):
    native: NativeWebSocketService = Inject()
    targets: WebSocketSessionUtils = Inject()
    convert: WebSocketConvert = Inject()

    @staticmethod
    def _message(value):
        return SocketMessage(
            type="infra-message",
            payload=value.model_dump(mode="json", by_alias=False),
            request_id=value.request_id,
        )

    async def send_message(self, session_id, message_type, message_content):
        return await self.send_object_message(
            session_id, message_type, WebsocketMessageVO(type=message_type, payload=message_content)
        )

    async def broadcast_message(self, message_type, message_content):
        return await self.broadcast_object_message(
            WebsocketMessageVO(type=message_type, payload=message_content)
        )

    async def send_object_message(self, session_id, message_type, message_content):
        return await self.native.send(
            self.targets.target(client_id=session_id), self._message(message_content)
        )

    async def broadcast_object_message(self, message_content):
        return await self.native.send(self.targets.target(), self._message(message_content))

    async def send_message_by_user_type(self, user_type, message_content):
        self._admin_type(user_type)
        return await self.broadcast_object_message(message_content)

    async def send_message_by_user_id(self, user_id, message_content):
        return await self.native.send(
            self.targets.target(member_id=str(user_id)), self._message(message_content)
        )

    async def send_to_user(self, user_type, user_id, message_content):
        self._admin_type(user_type)
        return await self.send_message_by_user_id(user_id, message_content)

    @staticmethod
    def _admin_type(user_type):
        if user_type != 2:
            raise IllegalArgumentException(msg="Infra 管理连接只接受管理员用户类型")

    async def get_active_connections(self):
        return {entry.client_id: entry for entry in await self.native.online(self.targets.target())}

    async def get_session_list(self, user_type=None, user_id=None):
        if user_type is not None:
            self._admin_type(user_type)
        return list(
            await self.native.online(
                self.targets.target(member_id=None if user_id is None else str(user_id))
            )
        )

    async def get_statistics(self):
        entries = await self.get_session_list()
        return {
            "total": len(entries),
            "users": len({entry.member_id for entry in entries}),
            "instances": len({entry.instance for entry in entries}),
        }

    async def get_status_info(self):
        if not self.convert.settings.enabled:
            return self.convert.build_status_info(0)
        return self.convert.build_status_info(len(await self.get_session_list()))
