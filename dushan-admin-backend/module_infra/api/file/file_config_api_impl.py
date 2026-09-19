from __future__ import annotations

from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.api.file.file_config_api import FileConfigApi
from module_infra.framework.file.core.client.file_client import FileClient
from module_infra.service.file.file_config_service import FileConfigService


@service(interface=FileConfigApi)
class FileConfigApiImpl(FileConfigApi):
    """文件配置 API 实现类"""

    file_config_service: FileConfigService = Inject()

    @override
    async def get_file_client(self, config_id: int) -> FileClient | None:
        """获取文件客户端"""
        if config_id is None or config_id < 0:
            raise ValueError("配置ID不能为空或小于0")
        return await self.file_config_service.get_file_client(config_id)

    @override
    async def get_master_file_client(self) -> FileClient | None:
        """获取主文件客户端"""
        return await self.file_config_service.get_master_file_client()
