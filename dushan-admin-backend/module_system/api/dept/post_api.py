from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from module_system.api.dept.dto.post_resp_dto import PostRespDTO


@runtime_checkable
class PostApi(Protocol):
    """岗位 API 接口"""

    async def valid_post_list(self, ids: Collection[int]) -> None:
        """校验岗位们是否有效"""
        ...

    async def get_post_list(self, ids: Collection[int]) -> list[PostRespDTO]:
        """获得岗位信息数组"""
        ...

    async def get_post_map(self, ids: Collection[int]) -> dict[int, PostRespDTO]:
        """获得指定编号的岗位 Map"""
        ...
