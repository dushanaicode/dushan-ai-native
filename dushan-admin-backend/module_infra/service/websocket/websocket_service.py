from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from framework.starter_websocket.public import (
    OnlineConnection,
)
from module_infra.controller.admin.websocket.vo.websocket_message_vo import WebsocketMessageVO


@runtime_checkable
class WebSocketService(Protocol):
    """WebSocket服务接口"""

    async def send_message(self, session_id: str, message_type: str, message_content: str) -> None:
        """向指定会话发送消息"""
        ...

    async def broadcast_message(self, message_type: str, message_content: str) -> None:
        """广播消息给所有连接的会话"""
        ...

    async def send_object_message(
        self, session_id: str, message_type: str, message_content: WebsocketMessageVO
    ) -> None:
        """向指定会话发送对象消息"""
        ...

    async def broadcast_object_message(self, message_content: WebsocketMessageVO) -> None:
        """广播对象消息给所有连接的会话"""
        ...

    async def send_message_by_user_type(
        self, user_type: int, message_content: WebsocketMessageVO
    ) -> None:
        """向指定用户类型的所有会话发送消息"""
        ...

    async def send_message_by_user_id(
        self, user_id: int, message_content: WebsocketMessageVO
    ) -> None:
        """向指定用户ID的所有会话发送消息"""
        ...

    async def send_to_user(
        self, user_type: int, user_id: int, message_content: WebsocketMessageVO
    ) -> None:
        """向指定用户发送消息（先按 user_id 查找，再按 user_type 兜底）"""
        ...

    async def get_active_connections(self) -> dict[str, OnlineConnection]:
        """获取所有活跃的WebSocket连接"""
        ...

    async def get_session_list(
        self, user_type: int | None = None, user_id: int | None = None
    ) -> list[OnlineConnection]:
        """获取符合条件的会话列表"""
        ...

    async def get_statistics(self) -> dict[str, Any]:
        """获取WebSocket服务统计信息"""
        ...

    async def get_status_info(self) -> dict[str, Any]:
        """获取WebSocket服务状态信息（配置 + 运行时）"""
        ...
