from __future__ import annotations

from typing import Collection, Protocol, runtime_checkable

from framework.common.page import PageResult
from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO
from module_system.controller.admin.dept.vo.post.post_save_req_vo import PostSaveReqVO
from module_system.dal.dataobject.dept.post_do import PostDO


@runtime_checkable
class PostService(Protocol):
    async def create_post(self, create_req_vo: PostSaveReqVO) -> int: ...

    async def update_post(self, update_req_vo: PostSaveReqVO) -> None: ...

    async def update_status(self, post_id: int, status: int) -> None: ...

    async def delete_post(self, id: int) -> None: ...

    async def delete_post_batch(self, ids: list[int]) -> int: ...

    async def get_post_list(
        self, ids: Collection[int] | None = None, statuses: Collection[int] | None = None
    ) -> list[PostDO]: ...

    async def get_post_page(self, req_vo: PostPageReqVO) -> PageResult[PostDO]: ...

    async def get_post(self, id: int) -> PostDO | None: ...

    async def get_post_names_by_ids(self, ids: Collection[int]) -> dict[int, str]:
        """批量读取岗位名称，忽略不存在的 ID。"""
        ...

    async def get_post_ids_by_names(self, names: Collection[str]) -> dict[str, int]:
        """批量解析岗位名称，拒绝重名歧义，忽略不存在的名称。"""
        ...

    async def validate_post_list(self, ids: Collection[int]) -> None: ...
