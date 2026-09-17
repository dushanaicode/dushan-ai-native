from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.permission.dto.role_resp_dto import RoleRespDTO


@runtime_checkable
class RoleApi(Protocol):
    """系统角色 API 接口"""

    async def valid_role_list(self, ids: Collection[int]) -> None:
        """校验角色列表有效"""
        ...

    async def get_role(self, id: int) -> RoleRespDTO | None:
        """获得角色信息"""
        ...

    async def get_role_list(self, ids: Collection[int]) -> list[RoleRespDTO]:
        """获得角色列表"""
        ...

    async def get_role_map(self, ids: Collection[int]) -> dict[int, RoleRespDTO]:
        """获得角色映射"""
        ...
