from __future__ import annotations

import json
from typing import override

from framework.common.enums.status_enum import StatusEnum
from framework.common.exception.exceptions.service_exception import ServiceException
from framework.common.page.schemas.page_result import PageResult
from framework.starter_config.config.config_settings import ConfigSettings
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_database.decorators.transactional import transactional
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_tenant.config.tenant_settings import TenantSettings
from module_infra.api.config.dto.config_group_dto import ConfigGroupDTO
from module_infra.api.config.dto.config_item_dto import ConfigItemDTO
from module_infra.controller.admin.config.vo.data.data_page_req_vo import ConfigDataPageReqVO
from module_infra.controller.admin.config.vo.data.data_resp_vo import ConfigDataRespVO
from module_infra.controller.admin.config.vo.data.data_save_req_vo import ConfigDataSaveReqVO
from module_infra.dal.dataobject.config.config_data_do import InfraConfigDataDO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO
from module_infra.dal.mapper.config.config_data_mapper import ConfigDataMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.config.config_data_service import ConfigDataService
from module_infra.service.config.config_type_service import ConfigTypeService
from module_system.api.auth.workload_api import WorkloadApi


@service(interface=ConfigDataService)
class ConfigDataServiceImpl(ConfigDataService):
    config_data_mapper: ConfigDataMapper = Inject()
    config_type_service: ConfigTypeService = Inject()
    config_provider: ConfigProvider = Inject()

    @override
    @transactional
    async def create_config(self, create_req_vo: ConfigDataSaveReqVO) -> int:
        await self._validate_config_type_exists(create_req_vo.type_id)
        await self._validate_config_key_unique(None, create_req_vo.key)
        config = InfraConfigDataDO(**create_req_vo.model_dump(by_alias=False))
        await self.config_data_mapper.insert(config)
        await self._schedule_refresh()
        return config.id

    @override
    @transactional
    async def update_config(self, update_req_vo: ConfigDataSaveReqVO) -> None:
        await self._validate_config_exists(update_req_vo.id)
        await self._validate_config_type_exists(update_req_vo.type_id)
        await self._validate_config_key_unique(update_req_vo.id, update_req_vo.key)
        update_obj = InfraConfigDataDO(**update_req_vo.model_dump(by_alias=False))
        await self.config_data_mapper.update_by_id(update_obj)
        await self._schedule_refresh()

    @override
    @transactional
    async def delete_config(self, config_id: int) -> None:
        await self._validate_config_exists(config_id)
        await self.config_data_mapper.delete_by_id(config_id)
        await self._schedule_refresh()

    @override
    @transactional
    async def delete_config_batch(self, config_ids: list[int]) -> int:
        deleted_count = await self.config_data_mapper.delete_by_ids(config_ids)
        await self._schedule_refresh()
        return deleted_count

    @override
    async def get_config(self, config_id: int) -> InfraConfigDataDO | None:
        return await self.config_data_mapper.select_by_id(config_id)

    @override
    async def get_config_with_type_name(self, config_id: int) -> ConfigDataRespVO | None:
        """根据ID获取配置，并关联配置类型名称"""
        config = await self.get_config(config_id)
        if config is None:
            return None
        config_resp_vo = ConfigDataRespVO.model_validate(config)
        if config.type_id:
            config_type = await self.config_type_service.get_config_type_by_id(config.type_id)
            if config_type:
                config_resp_vo.type_name = config_type.name
        return config_resp_vo

    @override
    async def get_config_by_key(self, key: str) -> InfraConfigDataDO | None:
        return await self.config_data_mapper.select_by_key(key)

    @override
    async def get_config_page(self, req_vo: ConfigDataPageReqVO) -> PageResult[InfraConfigDataDO]:
        return await self.config_data_mapper.select_page(req_vo)

    @override
    async def get_config_page_with_type_name(
        self, req_vo: ConfigDataPageReqVO
    ) -> PageResult[ConfigDataRespVO]:
        """分页获取配置列表，并关联配置类型名称"""
        module_type_ids = await self._get_module_type_ids(req_vo.module) if req_vo.module else None
        page_result: PageResult[InfraConfigDataDO] = await self.config_data_mapper.select_page(
            req_vo, module_type_ids
        )
        type_ids = list({item.type_id for item in page_result.items if item.type_id})
        type_map = await self._get_config_type_map(type_ids)
        resp_vos = self._convert_and_set_type_name(page_result.items, type_map)
        return PageResult(items=resp_vos, total=page_result.total)

    @override
    async def get_config_list_with_type_name(
        self, req_vo: ConfigDataPageReqVO = None
    ) -> list[ConfigDataRespVO]:
        """获取配置列表，并关联配置类型名称"""
        if req_vo:
            module_type_ids = (
                await self._get_module_type_ids(req_vo.module) if req_vo.module else None
            )
            page_result = await self.config_data_mapper.select_page(req_vo, module_type_ids)
            config_list = page_result.items
        else:
            config_list = await self.config_data_mapper.select_list()
        type_ids = list({item.type_id for item in config_list if item.type_id})
        type_map = await self._get_config_type_map(type_ids)
        return self._convert_and_set_type_name(config_list, type_map)

    @override
    async def get_config_list(self) -> list[InfraConfigDataDO]:
        return await self.config_data_mapper.select_list()

    @override
    async def get_config_count_by_type_id(self, type_id: int) -> int:
        return await self.config_data_mapper.select_count_by_type_id(type_id)

    @override
    async def get_config_with_type(self) -> list[tuple[InfraConfigDataDO, InfraConfigTypeDO]]:
        return await self.config_data_mapper.select_list_with_type()

    @override
    async def get_config_ids_by_type_id(self, type_id: int) -> list[int]:
        return await self.config_data_mapper.select_ids_by_type_id(type_id)

    @override
    async def get_value_by_module(self, module: str, key: str) -> str | None:
        """获取指定模块的配置值"""
        type_ids = await self._get_module_type_ids(module)
        if not type_ids:
            return None
        config = await self.config_data_mapper.select_by_key_in_types(type_ids, key)
        return config.value if config else None

    @override
    async def get_all_by_module(self, module: str) -> dict[str, str]:
        """获取指定模块下所有配置，返回 {key: value}"""
        type_ids = await self._get_module_type_ids(module)
        if not type_ids:
            return {}
        configs = await self.config_data_mapper.select_list_by_type_ids(type_ids)
        return {cfg.key: cfg.value for cfg in configs if cfg.key}

    @override
    async def get_values_by_type_code(self, module: str, type_code: str) -> dict[str, str]:
        """获取指定模块下某个 type_code 的所有配置"""
        config_type = await self.config_type_service.get_config_type_by_code(type_code)
        if config_type is None or config_type.module != module:
            return {}
        configs = await self.config_data_mapper.select_list_by_type_ids([config_type.id])
        return {cfg.key: cfg.value for cfg in configs if cfg.key}

    @override
    async def get_grouped_by_module(self, module: str) -> list[ConfigGroupDTO]:
        """获取指定模块下所有配置，按配置类型分组返回（含类型元数据）"""
        types = await self.config_type_service.get_config_types_by_module(module)
        if not types:
            return []
        type_ids = [t.id for t in types]
        configs = await self.config_data_mapper.select_list_by_type_ids(type_ids)
        config_map: dict[int, list[ConfigItemDTO]] = {}
        for cfg in configs:
            item = ConfigItemDTO(
                id=cfg.id,
                name=cfg.name,
                config_key=cfg.key,
                description=cfg.description,
                input_type=cfg.input_type or "input",
                input_props=cfg.input_props,
                content=cfg.value,
                sort=cfg.sort,
            )
            config_map.setdefault(cfg.type_id, []).append(item)
        return [
            ConfigGroupDTO(
                type_id=t.id, type_name=t.name, type_code=t.code, items=config_map.get(t.id, [])
            )
            for t in types
        ]

    @override
    @transactional
    async def update_value_by_module(self, module: str, key: str, value: str) -> None:
        """更新指定模块的配置值"""
        type_ids = await self._get_module_type_ids(module)
        if not type_ids:
            return
        config = await self.config_data_mapper.select_by_key_in_types(type_ids, key)
        if config:
            config.value = value
            await self.config_data_mapper.update_by_id(config)
            await self._schedule_refresh()

    @override
    @transactional
    async def batch_update_values_by_module(
        self, module: str, items: list[tuple[str, str]]
    ) -> None:
        """批量更新指定模块的配置值（单事务提交）"""
        type_ids = await self._get_module_type_ids(module)
        if not type_ids:
            return
        updated = False
        for key, value in items:
            config = await self.config_data_mapper.select_by_key_in_types(type_ids, key)
            if config:
                config.value = value
                await self.config_data_mapper.update_by_id(config)
                updated = True
        if updated:
            await self._schedule_refresh()

    async def _get_module_type_ids(self, module: str) -> list[int]:
        """获取模块对应的所有 type_id 列表"""
        types = await self.config_type_service.get_config_types_by_module(module)
        return [t.id for t in types]

    async def _validate_config_exists(self, config_id: int) -> InfraConfigDataDO:
        config = await self.config_data_mapper.select_by_id(config_id)
        if config is None:
            raise ServiceException(ErrorCodeConstants.CONFIG_DATA_NOT_EXISTS)
        return config

    async def _validate_config_type_exists(self, type_id: int) -> None:
        config_type = await self.config_type_service.get_config_type_by_id(type_id)
        if config_type is None:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_NOT_EXISTS)
        if config_type.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.CONFIG_TYPE_NOT_ENABLE)

    async def _validate_config_key_unique(self, config_id: int | None, key: str) -> None:
        config = await self.config_data_mapper.select_by_key(key)
        if config is not None and (config_id is None or config.id != config_id):
            raise ServiceException(ErrorCodeConstants.CONFIG_DATA_KEY_DUPLICATE)

    async def _get_config_type_map(self, type_ids: list[int]) -> dict[int, str]:
        """获取配置类型ID到名称的映射"""
        if not type_ids:
            return {}
        type_list = await self.config_type_service.get_config_type_list()
        return {t.id: t.name for t in type_list if t.id in set(type_ids)}

    @staticmethod
    def _convert_and_set_type_name(
        config_list: list[InfraConfigDataDO], type_map: dict[int, str]
    ) -> list[ConfigDataRespVO]:
        """转换配置对象为VO并设置类型名称"""
        resp_vos = []
        for item in config_list:
            resp_vo = ConfigDataRespVO.model_validate(item)
            if item.type_id in type_map:
                resp_vo.type_name = type_map[item.type_id]
            resp_vos.append(resp_vo)
        return resp_vos

    database: SessionProvider = Inject()
    config_settings: ConfigSettings = Inject()
    tenant_settings: TenantSettings = Inject()
    workloads: WorkloadApi = Inject()

    async def _schedule_refresh(self):
        if self.config_settings.reload_enabled:
            self.database.after_commit(self.refresh_config_source, name="infra-config-refresh")

    async def refresh_config_source(self):
        async with self.workloads.scope(
            "infra.config.sync", self.tenant_settings.default_tenant_id
        ):
            result = await self.config_provider.refresh_external(self.get_config_map)
            if result.listener_errors:
                raise ExceptionGroup("配置已提交但通知失败", list(result.listener_errors))

    async def get_config_map(self):
        values = {}
        for row in await self.get_config_list():
            try:
                value = json.loads(row.value)
            except json.JSONDecodeError:
                value = row.value
            values[row.key] = value
        return values
