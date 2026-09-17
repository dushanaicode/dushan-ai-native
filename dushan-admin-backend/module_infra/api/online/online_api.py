from typing import Protocol, runtime_checkable


@runtime_checkable
class OnlineApi(Protocol):
    """在线用户 API 接口"""

    async def force_logout(self, token_id: str) -> None:
        """强制指定 token_id 的用户下线"""
        ...
