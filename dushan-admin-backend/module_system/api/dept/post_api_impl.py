from __future__ import annotations

from typing import Collection, override

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.api.dept.dto.post_resp_dto import PostRespDTO
from module_system.api.dept.post_api import PostApi
from module_system.service.dept.post_service import PostService


@service(interface=PostApi)
class PostApiImpl(PostApi):
    """岗位 API 实现类"""

    post_service: PostService = Inject()

    @override
    async def valid_post_list(self, ids: Collection[int]) -> None:
        await self.post_service.validate_post_list(ids)

    @override
    async def get_post_list(self, ids: Collection[int]) -> list[PostRespDTO]:
        post_list = await self.post_service.get_post_list(ids)
        return [PostRespDTO.model_validate(post) for post in post_list]

    @override
    async def get_post_map(self, ids: Collection[int]) -> dict[int, PostRespDTO]:
        if not ids:
            return {}
        post_list = await self.get_post_list(ids)
        return {post.id: post for post in post_list}
