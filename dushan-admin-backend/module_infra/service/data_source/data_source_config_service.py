from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page import PageResult
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)
from module_infra.controller.admin.data_source.vo.data_source_config_save_req_vo import (
    DataSourceConfigSaveReqVO,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO


@runtime_checkable
class DataSourceConfigService(Protocol):
    """数据源配置服务接口"""

    async def create_data_source_config(self, create_req_vo: DataSourceConfigSaveReqVO) -> int:
        """创建数据源配置"""
        ...

    async def update_data_source_config(self, update_req_vo: DataSourceConfigSaveReqVO) -> None:
        """更新数据源配置"""
        ...

    async def update_status(self, data_source_config_id: int, status: int) -> None:
        """更新数据源配置状态"""
        ...

    async def delete_data_source_config(self, id: int) -> None:
        """删除数据源配置"""
        ...

    async def get_data_source_config(self, id: int) -> DataSourceConfigDO | None:
        """获取数据源配置"""
        ...

    async def get_data_source_config_page(
        self, page_req_vo: DataSourceConfigPageReqVO
    ) -> PageResult[DataSourceConfigDO]:
        """获取数据源配置分页"""
        ...

    async def get_data_source_config_list_by_status(self, status: int) -> list[DataSourceConfigDO]:
        """根据状态获取数据源配置列表"""
        ...

    async def get_data_source_config_list(self) -> list[DataSourceConfigDO]:
        """获取数据源配置列表"""
        ...

    async def get_default_data_source_config(self, source_type: int) -> DataSourceConfigDO | None:
        """获取默认数据源配置"""
        ...

    async def test_data_source_config(self, id: int) -> tuple[bool, str]:
        """测试数据源配置连接"""
        ...
