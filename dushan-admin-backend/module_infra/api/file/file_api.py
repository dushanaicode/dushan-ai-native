from typing import Protocol, runtime_checkable

from module_infra.api.file.dto.file_create_req_dto import FileCreateReqDTO
from module_infra.api.file.dto.file_presigned_url_resp_dto import FilePresignedUrlRespDTO
from module_infra.api.file.dto.file_upload_resp_dto import FileUploadRespDTO


@runtime_checkable
class FileApi(Protocol):
    """文件 API 接口，提供文件上传、预签名URL生成等功能"""

    async def create_file(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> str:
        """保存文件，并返回文件的访问路径"""
        ...

    async def presign_get_url(self, url: str, expiration_seconds: int | None = None) -> str:
        """生成文件预签名地址，用于读取"""
        ...

    async def get_presigned_upload_url(
        self, name: str, directory: str | None = None
    ) -> FilePresignedUrlRespDTO:
        """获取文件上传的预签名信息"""
        ...

    async def create_file_record(self, req: FileCreateReqDTO) -> int:
        """创建文件记录"""
        ...

    async def delete_file(self, file_id: int) -> None:
        """删除文件"""
        ...

    async def delete_file_by_storage_path(self, storage_path: str) -> bool:
        """通过存储路径删除文件"""
        ...

    async def create_file_with_id(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> tuple[int, str]:
        """保存文件，并返回文件ID和访问路径"""
        ...

    async def create_file_with_config(
        self,
        content: bytes,
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
