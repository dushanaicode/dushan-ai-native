from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_infra.controller.admin.server.vo.server_resp_vo import ServerMonitorRespVO
from module_infra.controller.admin.server.vo.server_usage_resp_vo import ServerUsageRespVO


@runtime_checkable
class ServerService(Protocol):
    """服务器信息管理服务接口"""

    async def get_server_list(self) -> ServerMonitorRespVO:
        """获取服务器监控信息列表"""
        ...

    async def get_server_usage(self) -> ServerUsageRespVO:
        """获取服务器监控精简信息"""
        ...
