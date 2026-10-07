from typing import Protocol, runtime_checkable

from module_infra.api.file.dto.file_upload_resp_dto import FileUploadRespDTO
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum


@runtime_checkable
class FileApi(Protocol):
    """文件 API 接口，提供文件上传、预签名URL生成等功能"""

    async def create_file(
        self,
        content: bytes,
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> str:
        """保存文件，并返回文件的访问路径"""
        ...

    async def presign_get_url(self, url: str, expiration_seconds: int | None = None) -> str:
        """生成文件预签名地址，用于读取"""
        ...

    async def delete_file(self, file_id: int) -> None:
        """删除文件"""
        ...

    async def delete_file_by_storage_path(self, config_id: int, storage_path: str) -> bool:
        """删除指定配置与路径的已登记文件，无元数据时返回 False。"""
        ...

    async def create_file_with_id(
        self,
        content: bytes,
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> tuple[int, str]:
        """保存文件，并返回文件ID和访问路径"""
        ...

    async def create_file_with_config(
        self,
        content: bytes,
        visibility: FileVisibilityEnum,
        config_id: int,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> tuple[int, str]:
        """使用指定存储配置保存文件，返回文件ID和访问路径"""
        ...

    async def upload_file(
        self,
        content: bytes,
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> "FileUploadRespDTO":
        """上传文件，返回完整的文件信息（含 config_id 和 storage_path）"""
        ...

    async def get_file_content(self, config_id: int, path: str) -> bytes:
        """获取文件内容"""
        ...

    async def get_content_by_url(self, url: str) -> bytes | None:
        """从 infra 文件 URL 解析 config_id + path 并读取文件内容"""
        ...
