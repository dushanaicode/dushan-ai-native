from __future__ import annotations

from typing import Collection, override

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_system.controller.admin.dict.vo.data.data_page_req_vo import DictDataPageReqVO
from module_system.controller.admin.dict.vo.data.data_save_req_vo import DictDataSaveReqVO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO
from module_system.dal.mapper.dict.dict_data_mapper import DictDataMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dict.dict_data_service import DictDataService
from module_system.service.dict.dict_type_service import DictTypeService


@service(interface=DictDataService)
class DictDataServiceImpl(DictDataService):
    """字典数据服务实现类"""

    dict_type_service: DictTypeService = Inject()
    dict_data_mapper: DictDataMapper = Inject()

    @override
    async def get_dict_data_list(self, status: int, dict_type: str | None) -> list[DictDataDO]:
        list_data = await self.dict_data_mapper.select_list_by_status_and_dict_type(
            status, dict_type
        )
        list_data.sort(key=lambda d: (d.dict_type, d.sort))
        return list_data

    @override
    async def get_dict_data(self, id: int) -> DictDataDO | None:
        return await self.dict_data_mapper.select_by_id(id)

    @override
    async def get_dict_data_page(self, page_req_vo: DictDataPageReqVO) -> PageResult[DictDataDO]:
        return await self.dict_data_mapper.select_page(page_req_vo)

    @override
    @transactional
    async def create_dict_data(self, create_req_vo: DictDataSaveReqVO) -> int:
        await self._validate_dict_type_exists(create_req_vo.dict_type)
        await self._validate_value_unique(None, create_req_vo.dict_type, create_req_vo.value)
        dict_data = DictDataDO(**create_req_vo.model_dump(by_alias=False))
        await self.dict_data_mapper.insert(dict_data)
        return dict_data.id

    @override
    @transactional
    async def update_dict_data(self, update_req_vo: DictDataSaveReqVO) -> None:
        await self._validate_exists(update_req_vo.id)
        await self._validate_dict_type_exists(update_req_vo.dict_type)
        await self._validate_value_unique(
            update_req_vo.id, update_req_vo.dict_type, update_req_vo.value
        )
        dict_data = DictDataDO(**update_req_vo.model_dump(by_alias=False))
        await self.dict_data_mapper.update_by_id(dict_data)

    @override
    @transactional
    async def update_status(self, dict_data_id: int, status: int) -> None:
        """更新字典数据状态"""
        await self._validate_exists(dict_data_id)
        update_obj = DictDataDO(id=dict_data_id, status=status)
        await self.dict_data_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def delete_dict_data(self, id: int) -> None:
        await self._validate_exists(id)
        await self.dict_data_mapper.delete_by_id(id)

    @override
    @transactional
    async def delete_dict_data_batch(self, ids: list[int]) -> int:
        data_list = await self.dict_data_mapper.select_by_ids(ids)
        if len(data_list) != len(ids):
            raise ServiceException(ErrorCodeConstants.DICT_DATA_NOT_EXISTS)
        return await self.dict_data_mapper.delete_by_ids(ids)

    @override
    async def get_dict_data_count_by_dict_type(self, dict_type: str) -> int:
        return await self.dict_data_mapper.select_count_by_dict_type(dict_type)

    @override
    async def validate_dict_data_list(self, dict_type: str, values: Collection[str]) -> None:
        if not values:
            return
        dict_data_list = await self.dict_data_mapper.select_by_dict_type_and_values(
            dict_type, values
        )
        dict_data_map = {data.value: data for data in dict_data_list}
        for value in values:
            dict_data = dict_data_map.get(value)
            if dict_data is None:
                raise ServiceException(ErrorCodeConstants.DICT_DATA_NOT_EXISTS)
            if dict_data.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.DICT_DATA_NOT_EXISTS, dict_data.label)

    @override
    async def get_dict_data_by_value(self, dict_type: str, value: str) -> DictDataDO | None:
        return await self.dict_data_mapper.select_by_dict_type_and_value(dict_type, value)

    @override
    async def parse_dict_data(self, dict_type: str, label: str) -> DictDataDO | None:
        return await self.dict_data_mapper.select_by_dict_type_and_label(dict_type, label)

    @override
    async def get_dict_data_list_by_dict_type(self, dict_type: str) -> list[DictDataDO]:
        list_data = await self.dict_data_mapper.select_list_by_field("dict_type", dict_type)
        list_data.sort(key=lambda d: d.sort)
        return list_data

    @override
    async def get_dict_data_list_by_dict_types(self, dict_types: list[str]) -> list[DictDataDO]:
        if not dict_types:
            return []
        list_data = await self.dict_data_mapper.select_list_by_dict_types(dict_types)
        list_data.sort(key=lambda d: d.sort)
        return list_data

    async def _validate_value_unique(self, id: int | None, dict_type: str, value: str) -> None:
        """校验字典数据的值是否唯一"""
        dict_data = await self.dict_data_mapper.select_by_dict_type_and_value(dict_type, value)
        if dict_data is None:
            return
        if id is None or dict_data.id != id:
            raise ServiceException(ErrorCodeConstants.DICT_DATA_VALUE_DUPLICATE)

    async def _validate_exists(self, id: int | None) -> None:
        """校验字典数据是否存在"""
        if id is None:
            return
        dict_data = await self.dict_data_mapper.select_by_id(id)
        if dict_data is None:
            raise ServiceException(ErrorCodeConstants.DICT_DATA_NOT_EXISTS)

    async def _validate_dict_type_exists(self, type_str: str) -> None:
        """校验字典类型是否存在且有效"""
        dict_type: DictTypeDO | None = await self.dict_type_service.get_dict_type_by_type(type_str)
        if dict_type is None:
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_NOT_EXISTS)
        if dict_type.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.DICT_TYPE_NOT_ENABLE)
