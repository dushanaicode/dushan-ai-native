from __future__ import annotations

from typing import Protocol, runtime_checkable

from module_infra.controller.admin.online.vo.online_info_req_vo import OnlineInfoReqVO
from module_infra.controller.admin.online.vo.online_resp_vo import OnlineInfoRespVO


@runtime_checkable
class OnlineService(Protocol):
    """在线用户管理服务接口"""

    async def get_online_list(self, query_object: OnlineInfoReqVO) -> list[OnlineInfoRespVO]:
        """获取在线用户列表"""
        ...

    async def force_logout(self, token_ids: str) -> None:
        """强制退出在线用户"""
        ...
