from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.file.vo.config.file_config_page_req_vo import FileConfigPageReqVO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.framework.file.core.client.file_client import FileClient


@runtime_checkable
class FileConfigService(Protocol):
    """文件配置服务接口"""

    async def create_file_config(self, create_req_vo) -> int:
        """创建文件配置"""
        ...

    async def update_file_config(self, update_req_vo) -> None:
        """更新文件配置"""
        ...

    async def update_file_config_master(self, file_config_id: int) -> None:
        """设置文件配置为主配置"""
        ...

    async def delete_file_config(self, file_config_id: int) -> None:
        """删除文件配置"""
        ...

    async def delete_file_config_batch(self, ids: list[int]) -> int:
        """批量删除文件配置"""
        ...

    async def get_file_config(self, file_config_id: int) -> FileConfigDO | None:
        """根据ID获取文件配置"""
        ...

    async def get_file_config_page(self, page_req_vo: FileConfigPageReqVO) -> PageResult:
        """分页获取文件配置列表"""
        ...

    async def get_file_config_list(self) -> list[FileConfigDO]:
        """获取文件配置列表"""
        ...

    async def test_file_config(self, file_config_id: int) -> str:
        """测试文件配置"""
        ...

    async def get_file_client(self, config_id: int) -> FileClient | None:
        """获取文件客户端"""
        ...

    async def get_master_file_client(self) -> FileClient | None:
        """获取主文件客户端"""
        ...
