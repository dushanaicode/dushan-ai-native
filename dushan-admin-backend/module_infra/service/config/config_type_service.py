from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.config.vo.type.type_page_req_vo import ConfigTypePageReqVO
from module_infra.controller.admin.config.vo.type.type_save_req_vo import ConfigTypeSaveReqVO
from module_infra.dal.dataobject.config.config_type_do import InfraConfigTypeDO


@runtime_checkable
class ConfigTypeService(Protocol):
    """配置类型服务接口"""

    async def get_config_type_page(
        self, page_req_vo: ConfigTypePageReqVO
    ) -> PageResult[InfraConfigTypeDO]:
        """分页查询配置类型数据"""
        ...

    async def get_config_type_by_id(self, id: int) -> InfraConfigTypeDO | None:
        """根据ID查询配置类型数据"""
        ...

    async def get_config_type_by_code(self, code: str) -> InfraConfigTypeDO | None:
        """根据配置类型编码查询配置类型数据"""
        ...

    async def create_config_type(self, create_req_vo: ConfigTypeSaveReqVO) -> int:
        """创建配置类型"""
        ...

    async def update_config_type(self, update_req_vo: ConfigTypeSaveReqVO) -> None:
        """更新配置类型"""
        ...

    async def update_status(self, config_type_id: int, status: int) -> None:
        """更新配置类型状态"""
        ...

    async def delete_config_type(self, id: int) -> None:
        """删除配置类型（逻辑删除）"""
        ...

    async def delete_config_type_batch(self, ids: list[int]) -> int:
        """批量删除配置类型（逻辑删除）"""
        ...

    async def get_config_type_list(self) -> list[InfraConfigTypeDO]:
        """查询所有配置类型数据"""
        ...

    async def get_config_types_by_module(self, module: str) -> list[InfraConfigTypeDO]:
        """根据模块标识查询所有启用的配置类型"""
        ...
