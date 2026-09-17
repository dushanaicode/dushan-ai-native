from __future__ import annotations

import re
from typing import override
from urllib.parse import unquote, urlsplit

from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from module_infra.api.file.dto.file_create_req_dto import FileCreateReqDTO
from module_infra.api.file.dto.file_presigned_url_resp_dto import FilePresignedUrlRespDTO
from module_infra.api.file.dto.file_upload_resp_dto import FileUploadRespDTO
from module_infra.api.file.file_api import FileApi
from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
from module_infra.service.file.file_service import FileService

_FILE_URL_PATTERN = re.compile("/(\\d+)/get/(.+)$")


@service(interface=FileApi)
class FileApiImpl(FileApi):
    """文件 API 实现类"""

    file_service: FileService = Inject()

    @override
    async def create_file(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> str:
        """保存文件，并返回文件的访问路径"""
        if not content:
            raise ValueError("文件内容不能为空")
        return await self.file_service.create_file(
            content=content, name=name, directory=directory, type_hint=type
        )

    @override
    async def presign_get_url(self, url: str, expiration_seconds: int | None = None) -> str:
        """生成文件预签名地址，用于读取"""
        if not url:
            raise ValueError("URL 不能为空")
        return await self.file_service.presign_get_url(url, expiration_seconds)

    @override
    async def delete_file(self, file_id: int) -> None:
        """删除文件"""
        if file_id is None or file_id <= 0:
            raise ValueError("文件ID不能为空或小于等于0")
        await self.file_service.delete_file(file_id)

    @override
    async def get_presigned_upload_url(
        self, name: str, directory: str | None = None
    ) -> FilePresignedUrlRespDTO:
        """获取直传的预签名信息（上传用）"""
        if not name:
            raise ValueError("文件名不能为空")
        resp = await self.file_service.get_file_presigned_url(name=name, directory=directory)
        return FilePresignedUrlRespDTO.model_validate(resp)

    @override
    async def create_file_record(self, req: FileCreateReqDTO) -> int:
        """在直传成功后创建文件记录"""
        if req is None:
            raise ValueError("请求体不能为空")
        values = req.model_dump(by_alias=False)
        values["config_id"] = str(req.config_id)
        req_vo = FileCreateReqVO.model_validate(values)
        return await self.file_service.create_file_record(req_vo)

    @override
    async def delete_file_by_storage_path(self, storage_path: str) -> bool:
        """通过存储路径删除文件（若存在）"""
        if not storage_path:
            return False
        return await self.file_service.delete_file_by_storage_path(storage_path)

    @override
    async def create_file_with_id(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> tuple[int, str]:
        """保存文件，并返回文件ID和访问路径"""
        if not content:
            raise ValueError("文件内容不能为空")
        return await self.file_service.create_file_with_id(
            content=content, name=name, directory=directory, type_hint=type
        )

    @override
    async def create_file_with_config(
        self,
        content: bytes,
        config_id: int,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> tuple[int, str]:
        """使用指定存储配置保存文件，返回文件ID和访问路径"""
        if not content:
            raise ValueError("文件内容不能为空")
        return await self.file_service.create_file_with_id(
            content=content, name=name, directory=directory, type_hint=type, config_id=config_id
        )

    @override
    async def upload_file(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type: str | None = None,
    ) -> FileUploadRespDTO:
        """上传文件，返回完整的文件信息（含 config_id 和 storage_path）"""
        if not content:
            raise ValueError("文件内容不能为空")
        file_id, url, config_id, storage_path = await self.file_service.create_file_full(
            content=content, name=name, directory=directory, type_hint=type
        )
        return FileUploadRespDTO(
            file_id=file_id, url=url, config_id=config_id, storage_path=storage_path
        )

    @override
    async def get_file_content(self, config_id: int, path: str) -> bytes:
        """获取文件内容"""
        if not path:
            raise ValueError("文件路径不能为空")
        return await self.file_service.get_file_content(config_id, path)

    @override
    async def get_content_by_url(self, url: str) -> bytes | None:
        match = _FILE_URL_PATTERN.search(urlsplit(url).path)
        if match is None:
            return None
        try:
            return await self.file_service.get_file_content(
                int(match.group(1)), unquote(match.group(2))
            )
        except FileNotFoundError:
            return None
