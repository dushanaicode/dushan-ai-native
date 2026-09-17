from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AuthAdminAuthApi(Protocol):
    """管理员认证 API 抽象接口"""

    async def logout(self, token: str, log_type: int) -> None:
        """基于 token 退出登录 API"""
        ...
