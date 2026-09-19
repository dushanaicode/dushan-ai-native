from __future__ import annotations

from datetime import datetime, timezone
from typing import override

from framework.common.dates import DateUtils
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.controller.admin.config.vo.type.type_page_req_vo import ConfigTypePageReqVO
from module_infra.controller.admin.config.vo.type.type_save_req_vo import ConfigTypeSaveReqVO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO
from module_infra.dal.mapper.config.config_data_mapper import ConfigDataMapper
from module_infra.dal.mapper.config.config_type_mapper import ConfigTypeMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.config.config_type_service import ConfigTypeService


@service(interface=ConfigTypeService)
class ConfigTypeServiceImpl(ConfigTypeService):
    config_type_mapper: ConfigTypeMapper = Inject()
    config_data_mapper: ConfigDataMapper = Inject()
    date_utils: DateUtils = Inject()

    @override
    async def get_config_type_page(
        self, page_req_vo: ConfigTypePageReqVO
    ) -> PageResult[InfraConfigTypeDO]:
        """分页查询配置类型数据"""
        return await self.config_type_mapper.select_page(page_req_vo)

    @override
    async def get_config_type_by_id(self, id: int) -> InfraConfigTypeDO | None:
        """根据 ID 查询配置类型数据"""
        return await self.config_type_mapper.select_by_id(id)

    @override
    async def get_config_type_by_code(self, code: str) -> InfraConfigTypeDO | None:
        """根据配置类型编码查询配置类型数据"""
        return await self.config_type_mapper.select_by_code(code)

    @override
    async def create_config_type(self, create_req_vo: ConfigTypeSaveReqVO) -> int:
        """创建配置类型"""
        await self._validate_config_type_name_unique(None, create_req_vo.name)
        await self._validate_config_type_code_unique(None, create_req_vo.code)
        config_type = InfraConfigTypeDO(**create_req_vo.model_dump(by_alias=False))
        await self.config_type_mapper.insert(config_type)
        return config_type.id

    @override
    async def update_config_type(self, update_req_vo: ConfigTypeSaveReqVO) -> None:
        """更新配置类型"""
        await self._validate_config_type_exists(update_req_vo.id)
        await self._validate_config_type_name_unique(update_req_vo.id, update_req_vo.name)
        await self._validate_config_type_code_unique(update_req_vo.id, update_req_vo.code)
        update_obj = InfraConfigTypeDO(**update_req_vo.model_dump(by_alias=False))
        await self.config_type_mapper.update_by_id(update_obj)

    @override
    async def update_status(self, config_type_id: int, status: int) -> None:
        """更新配置类型状态"""
        await self._validate_config_type_exists(config_type_id)
        update_obj = InfraConfigTypeDO(id=config_type_id, status=status)
        await self.config_type_mapper.update_by_id(update_obj)

    @override
    async def delete_config_type(self, id: int) -> None:
        """删除配置类型（逻辑删除）"""
        config_type = await self._validate_config_type_exists(id)
        count = await self.config_data_mapper.select_count_by_type_id(config_type.id)
        if count > 0:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_HAS_CHILDREN)
        await self.config_type_mapper.update_to_delete(
            id, datetime.now(timezone.utc).replace(tzinfo=None)
        )

    @override
    @transactional
    async def delete_config_type_batch(self, ids: list[int]) -> int:
        """批量逻辑删除配置类型；任一类型含配置数据时回滚整批。"""
        existing_types = await self.config_type_mapper.select_by_ids(ids)
        for config_type in existing_types:
            await self.delete_config_type(config_type.id)
        return len(existing_types)

    @override
    async def get_config_type_list(self) -> list[InfraConfigTypeDO]:
        """查询所有配置类型数据（未逻辑删除）"""
        return await self.config_type_mapper.select_list()

    @override
    async def get_config_types_by_module(self, module: str) -> list[InfraConfigTypeDO]:
        """根据模块标识查询所有启用的配置类型"""
        return await self.config_type_mapper.select_list_by_module(module)

    async def _validate_config_type_name_unique(self, id: int | None, name: str) -> None:
        """校验配置类型名称是否唯一"""
        config_type = await self.config_type_mapper.select_by_name(name)
        if config_type is None:
            return
        if id is None or config_type.id != id:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_NAME_DUPLICATE)

    async def _validate_config_type_code_unique(self, id: int | None, code: str) -> None:
        """校验配置类型编码是否唯一"""
        if not code:
            return
        config_type = await self.config_type_mapper.select_by_code(code)
        if config_type is None:
            return
        if id is None or config_type.id != id:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_CODE_DUPLICATE)

    async def _validate_config_type_exists(self, id: int | None) -> InfraConfigTypeDO | None:
        """校验配置类型是否存在"""
        if id is None:
            return None
        config_type = await self.config_type_mapper.select_by_id(id)
        if config_type is None:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_NOT_EXISTS)
        return config_type
