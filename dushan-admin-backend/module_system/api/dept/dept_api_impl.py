from __future__ import annotations

from typing import Collection, override

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.dept.dept_api import DeptApi
from module_system.api.dept.dto.dept_resp_dto import DeptRespDTO
from module_system.service.dept.dept_service import DeptService


@service(interface=DeptApi)
class DeptApiImpl(DeptApi):
    """部门 API 实现类"""

    dept_service: DeptService = Inject()

    @override
    async def get_dept(self, id: int) -> DeptRespDTO:
        dept = await self.dept_service.get_dept(id)
        return DeptRespDTO.model_validate(dept)

    @override
    async def get_dept_list(self, ids: Collection[int]) -> list[DeptRespDTO]:
        depts = await self.dept_service.get_dept_list_by_ids(ids)
        return [DeptRespDTO.model_validate(dept) for dept in depts]

    @override
    async def validate_dept_list(self, ids: Collection[int]) -> None:
        await self.dept_service.validate_dept_list(ids)

    @override
    async def get_dept_map(self, ids: Collection[int]) -> dict[int, DeptRespDTO]:
        if not ids:
            return {}
        dept_list = await self.get_dept_list(ids)
        return {dept.id: dept for dept in dept_list}

    @override
    async def get_child_dept_list(self, id: int) -> list[DeptRespDTO]:
        child_dept_list = await self.dept_service.get_child_dept_list(id)
        return [DeptRespDTO.model_validate(dept) for dept in child_dept_list]
