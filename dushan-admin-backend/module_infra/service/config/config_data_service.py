from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.api.config.dto.config_group_dto import ConfigGroupDTO
from module_infra.controller.admin.config.vo.data.data_page_req_vo import ConfigDataPageReqVO
from module_infra.controller.admin.config.vo.data.data_resp_vo import ConfigDataRespVO
from module_infra.controller.admin.config.vo.data.data_save_req_vo import ConfigDataSaveReqVO
from module_infra.dal.dataobject.config.config_data_do import InfraConfigDataDO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO


@runtime_checkable
class ConfigDataService(Protocol):
    """配置数据服务接口"""

    async def create_config(self, create_req_vo: ConfigDataSaveReqVO) -> int:
        """创建配置"""
        ...

    async def update_config(self, update_req_vo: ConfigDataSaveReqVO) -> None:
        """更新配置"""
        ...

    async def delete_config(self, config_id: int) -> None:
        """删除配置"""
        ...

    async def delete_config_batch(self, config_ids: list[int]) -> int:
        """批量删除配置"""
        ...

    async def get_config_ids_by_type_id(self, type_id: int) -> list[int]:
        """根据配置类型ID获取配置数据ID列表"""
        ...

    async def get_config(self, config_id: int) -> InfraConfigDataDO | None:
        """根据ID获取配置"""
        ...

    async def get_config_with_type_name(self, config_id: int) -> ConfigDataRespVO | None:
        """根据ID获取配置，并关联配置类型名称"""
        ...

    async def get_config_by_key(self, key: str) -> InfraConfigDataDO | None:
        """根据键获取配置"""
        ...

    async def get_config_page(self, req_vo: ConfigDataPageReqVO) -> PageResult[InfraConfigDataDO]:
        """分页获取配置列表"""
        ...

    async def get_config_page_with_type_name(
        self, req_vo: ConfigDataPageReqVO
    ) -> PageResult[ConfigDataRespVO]:
        """分页获取配置列表，并关联配置类型名称"""
        ...

    async def get_config_list_with_type_name(
        self, req_vo: ConfigDataPageReqVO = None
    ) -> list[ConfigDataRespVO]:
        """获取配置列表，并关联配置类型名称"""
        ...

    async def get_config_list(self) -> list[InfraConfigDataDO]:
        """获取所有配置列表"""
        ...

    async def get_config_count_by_type_id(self, type_id: int) -> int:
        """根据配置类型ID获取配置数量"""
        ...

    async def get_config_with_type(self) -> list[tuple[InfraConfigDataDO, InfraConfigTypeDO]]:
        """获取配置数据并关联配置类型"""
        ...

    async def refresh_config_source(self) -> None:
        """刷新配置源"""
        ...

    async def get_config_map(self) -> dict[str, Any]:
        """获取所有配置键值映射"""
        ...

    async def get_value_by_module(self, module: str, key: str) -> str | None:
        """获取指定模块的配置值"""
        ...

    async def get_all_by_module(self, module: str) -> dict[str, str]:
        """获取指定模块下所有配置，返回 {key: value}"""
        ...

    async def get_values_by_type_code(self, module: str, type_code: str) -> dict[str, str]:
        """获取指定模块下某个 type_code 的所有配置"""
        ...

    async def get_grouped_by_module(self, module: str) -> list[ConfigGroupDTO]:
        """获取指定模块下所有配置，按配置类型分组返回（含类型元数据）"""
        ...

    async def update_value_by_module(self, module: str, key: str, value: str) -> None:
        """更新指定模块的配置值"""
        ...

    async def batch_update_values_by_module(
        self, module: str, items: list[tuple[str, str]]
    ) -> None:
        """批量更新指定模块的配置值（单事务提交）"""
        ...
