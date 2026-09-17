from typing import Protocol, runtime_checkable

from module_infra.framework.file.core.client.file_client import FileClient


@runtime_checkable
class FileConfigApi(Protocol):
    """文件配置 API 接口"""

    async def get_file_client(self, config_id: int) -> FileClient | None:
        """获取文件客户端"""
        ...

    async def get_master_file_client(self) -> FileClient | None:
        """获取主文件客户端"""
        ...
