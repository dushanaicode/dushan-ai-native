from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TenantMenuHandler(Protocol):
    """租户菜单处理器接口"""

    async def handle(self, menu_ids: set[int]) -> None: ...
