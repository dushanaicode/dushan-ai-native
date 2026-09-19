from __future__ import annotations

from typing import Collection, override

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.starter_cache.public import CacheHandler, cache
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.dept.vo.dept.dept_list_req_vo import DeptListReqVO
from module_system.controller.admin.dept.vo.dept.dept_save_req_vo import DeptSaveReqVO
from module_system.dal.cache.cache_key_constants import SystemCacheKeys
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.mapper.dept.dept_mapper import DeptMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.dept_service import DeptService
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)

_DEPT_CACHE_KEY = SystemCacheKeys.DEPT_CHILDREN_ID_LIST


@service(interface=DeptService)
class DeptServiceImpl(DeptService):
    revisions: AuthorizationRevisionService = Inject()
    cache_handler: CacheHandler = Inject()
    database: SessionProvider = Inject()
    "部门服务实现类"
    dept_mapper: DeptMapper = Inject()

    @override
    @transactional
    async def create_dept(self, create_req_vo: DeptSaveReqVO) -> int:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(_DEPT_CACHE_KEY),
            required=True,
            name="system-cache",
        )
        if create_req_vo.parent_id is None:
            create_req_vo.parent_id = "0"
        await self._validate_parent_dept(None, create_req_vo.parent_id)
        await self._validate_dept_name_unique(None, create_req_vo.parent_id, create_req_vo.name)
        dept = DeptDO(**create_req_vo.model_dump(exclude_unset=True, by_alias=False))
        dept = await self.dept_mapper.insert(dept)
        return dept.id

    @override
    @transactional
    async def update_dept(self, update_req_vo: DeptSaveReqVO) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(_DEPT_CACHE_KEY),
            required=True,
            name="system-cache",
        )
        if update_req_vo.parent_id is None:
            update_req_vo.parent_id = "0"
        await self._validate_dept_exists(update_req_vo.id)
        await self._validate_parent_dept(update_req_vo.id, update_req_vo.parent_id)
        await self._validate_dept_name_unique(
            update_req_vo.id, update_req_vo.parent_id, update_req_vo.name
        )
        update_obj = DeptDO(**update_req_vo.model_dump(exclude_unset=True, by_alias=False))
        await self.dept_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, dept_id: int, status: int) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(_DEPT_CACHE_KEY),
            required=True,
            name="system-cache",
        )
        "更新部门状态"
        await self._validate_dept_exists(dept_id)
        update_obj = DeptDO(id=dept_id, status=status)
        await self.dept_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_dept(self, id: int) -> None:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(_DEPT_CACHE_KEY),
            required=True,
            name="system-cache",
        )
        await self._validate_dept_exists(id)
        count = await self.dept_mapper.select_count_by_parent_id(id)
        if count > 0:
            raise ServiceException(ErrorCodeConstants.DEPT_EXITS_CHILDREN)
        await self.dept_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_dept_batch(self, ids: list[int]) -> int:
        await self.revisions.advance()
        self.database.after_commit(
            lambda: self.cache_handler.delete_all(_DEPT_CACHE_KEY),
            required=True,
            name="system-cache",
        )
        if await self.dept_mapper.count(DeptDO.parent_id.in_(ids), DeptDO.id.not_in(ids)):
            raise ServiceException(ErrorCodeConstants.DEPT_EXITS_CHILDREN)
        return await self.dept_mapper.delete_by_ids(ids)

    @override
    async def get_dept(self, dept_id: int) -> DeptDO | None:
        return await self.dept_mapper.select_by_id(dept_id)

    @override
    async def get_dept_list_by_ids(self, ids: Collection[int]) -> list[DeptDO]:
        if not ids:
            return []
        return await self.dept_mapper.select_batch_ids(ids)

    @override
    async def get_dept_list(self, req_vo: DeptListReqVO) -> list[DeptDO]:
        dept_list = await self.dept_mapper.select_list_by_vo(req_vo)
        return sorted(dept_list, key=lambda d: d.sort)

    @override
    async def get_child_dept_list(self, id: int) -> list[DeptDO]:
        return await self.get_child_dept_list_by_ids([id])

    @override
    async def get_dept_list_by_leader_user_id(self, user_id: int) -> list[DeptDO]:
        return await self.dept_mapper.select_list_by_leader_user_id(user_id)

    @override
    async def get_dept_list_by_status(self, status: int) -> list[DeptDO]:
        return await self.dept_mapper.select_list_by_status(status)

    @override
    async def validate_dept_list(self, ids: Collection[int]) -> None:
        if not ids:
            return
        dept_list = await self.get_dept_list_by_ids(ids)
        dept_map = {dept.id: dept for dept in dept_list}
        for dept_id in ids:
            dept = dept_map.get(dept_id)
            if dept is None:
                raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
            if dept.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.DEPT_NOT_ENABLE, dept.name)

    @override
    async def get_dept_map(self, ids: Collection[int]) -> dict[int, DeptDO]:
        dept_list = await self.get_dept_list_by_ids(ids)
        return {dept.id: dept for dept in dept_list}

    @override
    async def get_child_dept_list_by_ids(self, ids: Collection[int]) -> list[DeptDO]:
        if not ids:
            return []
        children: list[DeptDO] = []
        parent_ids = list(ids)
        while parent_ids:
            depts = await self.dept_mapper.select_list_by_parent_id(parent_ids)
            if not depts:
                break
            children.extend(depts)
            parent_ids = [dept.id for dept in depts]
        return children

    @cache(_DEPT_CACHE_KEY, key="{{id}}", ttl_seconds=3600)
    @override
    async def get_child_dept_id_list_from_cache(self, id: int) -> set[int]:
        depts = await self.get_dept_list(DeptListReqVO())
        result: set[int] = set()
        self._collect_child_ids(id, depts, result)
        return result

    def _collect_child_ids(self, parent_id: int, all_depts: list[DeptDO], result: set[int]) -> None:
        """递归收集子部门 ID"""
        for dept in all_depts:
            if dept.parent_id == parent_id:
                result.add(dept.id)
                self._collect_child_ids(dept.id, all_depts, result)

    async def _validate_dept_exists(self, dept_id: int | None) -> None:
        if dept_id is None:
            return
        dept = await self.dept_mapper.select_by_id(dept_id)
        if dept is None:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)

    async def _validate_parent_dept(self, dept_id: int | None, parent_id: int | None) -> None:
        if parent_id is None or parent_id == DeptDO.PARENT_ID_ROOT:
            return
        if dept_id is not None and dept_id == parent_id:
            raise ServiceException(ErrorCodeConstants.DEPT_PARENT_ERROR)
        parent_dept = await self.dept_mapper.select_by_id(parent_id)
        if parent_dept is None:
            raise ServiceException(ErrorCodeConstants.DEPT_PARENT_NOT_EXITS)
        if dept_id is None:
            return
        current_parent_id = parent_dept.parent_id
        for _ in range(32767):
            if dept_id == current_parent_id:
                raise ServiceException(ErrorCodeConstants.DEPT_PARENT_IS_CHILD)
            if current_parent_id is None or current_parent_id == DeptDO.PARENT_ID_ROOT:
                break
            parent_dept = await self.dept_mapper.select_by_id(parent_dept.parent_id)
            if parent_dept is None:
                break
            current_parent_id = parent_dept.parent_id

    async def _validate_dept_name_unique(
        self, dept_id: int | None, parent_id: int, name: str
    ) -> None:
        dept = await self.dept_mapper.select_by_parent_id_and_name(parent_id, name)
        if dept is None:
            return
        if dept_id is None or dept.id != dept_id:
            raise ServiceException(ErrorCodeConstants.DEPT_NAME_DUPLICATE)
