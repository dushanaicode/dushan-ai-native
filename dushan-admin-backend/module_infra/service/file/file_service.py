from __future__ import annotations

from typing import Protocol, runtime_checkable

from framework.common.page.schemas.page_result import PageResult
from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
from module_infra.controller.admin.file.vo.file.file_list_objects_resp_vo import (
    FileListObjectsRespVO,
)
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.controller.admin.file.vo.file.file_presigned_url_resp_vo import (
    FilePresignedUrlRespVO,
)
from module_infra.controller.admin.file.vo.file.file_search_req_vo import FileSearchReqVO
from module_infra.dal.dataobject.file.file_do import FileDO


@runtime_checkable
class FileService(Protocol):
    """文件服务接口"""

    async def get_file_page(self, req_vo: FilePageReqVO) -> PageResult[FileDO]:
        """获取文件分页列表"""
        ...

    async def create_file(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> str:
        """创建文件（上传文件内容），返回文件访问URL。config_id 不传则使用 master 配置"""
        ...

    async def create_file_record(self, create_req_vo: FileCreateReqVO) -> int:
        """创建文件记录"""
        ...

    async def delete_file(self, file_id: int) -> None:
        """删除文件"""
        ...

    async def delete_file_by_storage_path(self, storage_path: str) -> bool:
        """通过存储路径删除文件"""
        ...

    async def get_file_content(self, config_id: int, path: str) -> bytes:
        """获取文件内容"""
        ...

    async def get_file_presigned_url(
        self, name: str, directory: str | None = None
    ) -> FilePresignedUrlRespVO:
        """获取文件预签名URL"""
        ...

    async def create_file_by_vo(self, create_req_vo: FileCreateReqVO) -> int:
        """通过VO创建文件"""
        ...

    async def get_file_count_by_config_id(self, config_id: int) -> int:
        """根据配置ID统计文件数量"""
        ...

    async def delete_file_batch(self, ids: list[int]) -> int:
        """批量删除文件"""
        ...

    async def create_file_with_id(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> tuple[int, str]:
        """创建文件并返回文件ID和访问URL"""
        ...

    async def create_file_full(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> tuple[int, str, int, str]:
        """创建文件并返回完整信息 (file_id, url, config_id, storage_path)"""
        ...

    async def presign_get_url(self, url: str, expiration_seconds: int | None = None) -> str:
        """生成文件预签名地址，用于读取"""
        ...

    async def list_objects(
        self, config_id: int, prefix: str, delimiter: str
    ) -> FileListObjectsRespVO:
        """列举指定存储配置下的目录和文件"""
        ...

    async def create_directory(self, config_id: int, directory_path: str) -> None:
        """在指定存储配置下创建目录"""
        ...

    async def search_files(self, req_vo: FileSearchReqVO) -> PageResult[FileDO]:
        """搜索文件（模糊/前缀）"""
        ...

    async def delete_by_key(self, config_id: int, key: str) -> None:
        """通过存储配置ID和文件key删除文件（同时清理DB记录）"""
        ...

    async def delete_by_keys(self, config_id: int, keys: list[str]) -> int:
        """批量通过存储配置ID和文件key删除文件"""
        ...

    async def rename_object(self, config_id: int, old_key: str, new_name: str) -> None:
        """重命名文件或目录"""
        ...
