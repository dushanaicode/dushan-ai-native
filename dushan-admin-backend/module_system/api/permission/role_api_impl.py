from __future__ import annotations

from typing import Collection, override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.api.permission.dto.role_resp_dto import RoleRespDTO
from module_system.api.permission.role_api import RoleApi
from module_system.service.permission.role_service import RoleService


@service(interface=RoleApi)
class RoleApiImpl(RoleApi):
    """系统角色 API 实现类"""

    role_service: RoleService = Inject()

    @override
    async def valid_role_list(self, ids: Collection[int]) -> None:
        """校验角色列表有效"""
        await self.role_service.validate_role_list(ids)

    @override
    async def get_role(self, id: int) -> RoleRespDTO | None:
        """获得角色信息"""
        role = await self.role_service.get_role(id)
        if role is None:
            return None
        return RoleRespDTO.model_validate(role)

    @override
    async def get_role_list(self, ids: Collection[int]) -> list[RoleRespDTO]:
        """获得角色信息数组"""
        roles = await self.role_service.get_role_list_by_ids(ids)
        return [RoleRespDTO.model_validate(role) for role in roles]

    @override
    async def get_role_map(self, ids: Collection[int]) -> dict[int, RoleRespDTO]:
        """获得指定编号的角色 Map"""
        if not ids:
            return {}
        role_list = await self.get_role_list(ids)
        return {role.id: role for role in role_list}
