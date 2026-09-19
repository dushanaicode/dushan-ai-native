from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO
from module_system.controller.admin.dict.vo.type.type_save_req_vo import DictTypeSaveReqVO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO
from module_system.dal.mapper.dict.dict_data_mapper import DictDataMapper
from module_system.dal.mapper.dict.dict_type_mapper import DictTypeMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dict.dict_type_service import DictTypeService


@service(interface=DictTypeService)
class DictTypeServiceImpl(DictTypeService):
    """字典类型服务实现类"""

    dict_type_mapper: DictTypeMapper = Inject()
    dict_data_mapper: DictDataMapper = Inject()

    @override
    async def get_dict_type_page(self, page_req_vo: DictTypePageReqVO) -> PageResult[DictTypeDO]:
        return await self.dict_type_mapper.select_page(page_req_vo)

    @override
    async def get_dict_type_by_id(self, id: int) -> DictTypeDO | None:
        return await self.dict_type_mapper.select_by_id(id)

    @override
    async def get_dict_type_by_type(self, type_str: str) -> DictTypeDO | None:
        return await self.dict_type_mapper.select_by_type(type_str)

    @override
    @transactional
    async def create_dict_type(self, create_req_vo: DictTypeSaveReqVO) -> int:
        await self._validate_name_unique(None, create_req_vo.name)
        await self._validate_type_unique(None, create_req_vo.type)
        dict_type = DictTypeDO(**create_req_vo.model_dump(by_alias=False))
        await self.dict_type_mapper.insert(dict_type)
        return dict_type.id

    @override
    @transactional
    async def update_dict_type(self, update_req_vo: DictTypeSaveReqVO) -> None:
        await self._validate_exists(update_req_vo.id)
        await self._validate_name_unique(update_req_vo.id, update_req_vo.name)
        await self._validate_type_unique(update_req_vo.id, update_req_vo.type)
        update_obj = DictTypeDO(**update_req_vo.model_dump(by_alias=False))
        await self.dict_type_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_status(self, dict_type_id: int, status: int) -> None:
        """更新字典类型状态"""
        await self._validate_exists(dict_type_id)
        update_obj = DictTypeDO(id=dict_type_id, status=status)
        await self.dict_type_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_dict_type(self, id: int) -> None:
        dict_type = await self._validate_exists(id)
        data_list = await self.dict_data_mapper.select_list_by_field("dict_type", dict_type.type)
        if data_list:
            await self.dict_data_mapper.delete_by_ids([d.id for d in data_list])
        await self.dict_type_mapper.update_to_delete(
            id, datetime.now(timezone.utc).replace(tzinfo=None)
        )

    @override
    @transactional
    async def delete_dict_type_batch(self, ids: list[int]) -> int:
        dict_types = await self.dict_type_mapper.select_by_ids(ids)
        if len(dict_types) != len(ids):
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_NOT_EXISTS)
        type_strings = [t.type for t in dict_types]
        if type_strings:
            all_data_list = await self.dict_data_mapper.select_list_by_dict_types(type_strings)
            if all_data_list:
                data_ids = list({d.id for d in all_data_list})
                await self.dict_data_mapper.delete_by_ids(data_ids)
        return await self.dict_type_mapper.delete_by_ids(ids)

    @override
    async def get_dict_type_list(self) -> list[DictTypeDO]:
        return await self.dict_type_mapper.select_list()

    async def _validate_name_unique(self, id: int | None, name: str) -> None:
        """校验字典类型名称是否唯一"""
        dict_type = await self.dict_type_mapper.select_by_name(name)
        if dict_type is None:
            return
        if id is None or dict_type.id != id:
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_NAME_DUPLICATE)

    async def _validate_type_unique(self, id: int | None, type_str: str) -> None:
        """校验字典类型是否唯一"""
        if not type_str:
            return
        dict_type = await self.dict_type_mapper.select_by_type(type_str)
        if dict_type is None:
            return
        if id is None or dict_type.id != id:
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_TYPE_DUPLICATE)

    async def _validate_exists(self, id: int | None) -> DictTypeDO | None:
        """校验字典类型是否存在，存在时返回"""
        if id is None:
            return None
        dict_type = await self.dict_type_mapper.select_by_id(id)
        if dict_type is None:
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_NOT_EXISTS)
        return dict_type
