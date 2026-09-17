from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.dept.dto.dept_resp_dto import DeptRespDTO


@runtime_checkable
class DeptApi(Protocol):
    """部门 API 接口"""

    async def get_dept(self, id: int) -> DeptRespDTO:
        """获得部门信息"""
        ...

    async def get_dept_list(self, ids: Collection[int]) -> list[DeptRespDTO]:
        """获得部门信息数组"""
        ...

    async def validate_dept_list(self, ids: Collection[int]) -> None:
        """校验部门们是否有效"""
        ...

    async def get_dept_map(self, ids: Collection[int]) -> dict[int, DeptRespDTO]:
        """获得指定编号的部门 Map"""
        ...

    async def get_child_dept_list(self, id: int) -> list[DeptRespDTO]:
        """获得指定部门的所有子部门"""
        ...
