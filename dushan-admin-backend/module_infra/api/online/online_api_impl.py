from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.api.online.online_api import OnlineApi
from module_infra.service.online.online_service import OnlineService


@service(interface=OnlineApi)
class OnlineApiImpl(OnlineApi):
    """在线用户 API 接口"""

    online_service: OnlineService = Inject()

    @override
    async def force_logout(self, token_id: str) -> None:
        """强制指定 token_id 的用户下线"""
        if not token_id:
            raise ValueError("token_id 不能为空")
        await self.online_service.force_logout(token_id)
