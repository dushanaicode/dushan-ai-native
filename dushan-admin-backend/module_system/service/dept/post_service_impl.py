from __future__ import annotations

from typing import Collection, override

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_database.decorators.transactional import transactional
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO
from module_system.controller.admin.dept.vo.post.post_save_req_vo import PostSaveReqVO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.mapper.dept.post_mapper import PostMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.post_service import PostService


@service(interface=PostService)
class PostServiceImpl(PostService):
    """岗位服务实现类"""

    post_mapper: PostMapper = Inject()

    @override
    @transactional
    async def create_post(self, create_req_vo: PostSaveReqVO) -> int:
        await self._validate_for_create_or_update(None, create_req_vo.name, create_req_vo.code)
        post = PostDO(**create_req_vo.model_dump(by_alias=False))
        await self.post_mapper.insert(post)
        return post.id

    @override
    @transactional
    async def update_post(self, update_req_vo: PostSaveReqVO) -> None:
        await self._validate_for_create_or_update(
            update_req_vo.id, update_req_vo.name, update_req_vo.code
        )
        update_obj = PostDO(**update_req_vo.model_dump(by_alias=False))
        await self.post_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, post_id: int, status: int) -> None:
        """更新岗位状态"""
        await self._validate_exists(post_id)
        update_obj = PostDO(id=post_id, status=status)
        await self.post_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_post(self, id: int) -> None:
        await self._validate_exists(id)
        await self.post_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_post_batch(self, ids: list[int]) -> int:
        for post_id in ids:
            await self._validate_exists(post_id)
        return await self.post_mapper.delete_by_ids(ids)

    @override
    async def get_post_list(
        self, ids: Collection[int] | None = None, statuses: Collection[int] | None = None
    ) -> list[PostDO]:
        if ids is not None and len(ids) == 0:
            return []
        return await self.post_mapper.select_list(ids, statuses)

    @override
    async def get_post_page(self, req_vo: PostPageReqVO) -> PageResult[PostDO]:
        return await self.post_mapper.select_page(req_vo)

    @override
    async def get_post(self, id: int) -> PostDO | None:
        return await self.post_mapper.select_by_id(id)

    @override
    async def validate_post_list(self, ids: Collection[int]) -> None:
        if not ids:
            return
        posts = await self.post_mapper.select_batch_ids(ids)
        post_map = {post.id: post for post in posts}
        for pid in ids:
            post = post_map.get(pid)
            if post is None:
                raise ServiceException(ErrorCodeConstants.POST_NOT_FOUND)
            if post.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.POST_NOT_ENABLE, post.name)

    async def _validate_for_create_or_update(self, id: int | None, name: str, code: str) -> None:
        """校验岗位创建或更新的参数"""
        await self._validate_exists(id)
        await self._validate_name_unique(id, name)
        await self._validate_code_unique(id, code)

    async def _validate_exists(self, id: int | None) -> None:
        if id is None:
            return
        post = await self.post_mapper.select_by_id(id)
        if post is None:
            raise ServiceException(ErrorCodeConstants.POST_NOT_FOUND)

    async def _validate_name_unique(self, id: int | None, name: str) -> None:
        post = await self.post_mapper.select_by_name(name)
        if post is None:
            return
        if id is None or post.id != id:
            raise ServiceException(ErrorCodeConstants.POST_NAME_DUPLICATE)

    async def _validate_code_unique(self, id: int | None, code: str) -> None:
        post = await self.post_mapper.select_by_code(code)
        if post is None:
            return
        if id is None or post.id != id:
            raise ServiceException(ErrorCodeConstants.POST_CODE_DUPLICATE)
