from __future__ import annotations

import hashlib
import os
import time
from typing import override
from urllib.parse import quote

from framework.common.exception import (
    IllegalArgumentException,
    ServiceException,
)
from framework.common.page import PageResult
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
from module_infra.controller.admin.file.vo.file.file_list_objects_resp_vo import (
    FileListObjectsRespVO,
)
from module_infra.controller.admin.file.vo.file.file_object_vo import FileObjectVO
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.controller.admin.file.vo.file.file_presigned_url_resp_vo import (
    FilePresignedUrlRespVO,
)
from module_infra.controller.admin.file.vo.file.file_search_req_vo import FileSearchReqVO
from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.framework.file.core.client.file_client import FileClient
from module_infra.framework.file.core.client.s3.s3_file_client import S3FileClient
from module_infra.framework.file.core.client.s3.s3_file_presigned_url_resp_dto import (
    FilePresignedUrlRespDTO,
)
from module_infra.framework.file.core.utils.file_type_utils import FileTypeUtils
from module_infra.service.file.file_config_service import FileConfigService
from module_infra.service.file.file_service import FileService


@service(interface=FileService)
class FileServiceImpl(FileService):
    PATH_SUFFIX_TIMESTAMP_ENABLE: bool = True
    file_mapper: FileMapper = Inject()
    file_config_service: FileConfigService = Inject()

    @override
    async def get_file_page(self, req_vo: FilePageReqVO) -> PageResult[FileDO]:
        return await self.file_mapper.select_page(req_vo)

    @override
    async def create_file(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> str:
        """保存文件并返回访问 URL。config_id 不传则使用 master 配置"""
        _, url = await self.create_file_with_id(
            content=content,
            name=name,
            directory=directory,
            type_hint=type_hint,
            path=path,
            config_id=config_id,
        )
        return url

    @override
    async def create_file_record(self, create_req_vo: FileCreateReqVO) -> int:
        """通过请求 VO 创建文件记录"""
        req = create_req_vo.model_dump(by_alias=False)
        await self._get_file_client(create_req_vo.config_id)
        AbstractFileClient.key(create_req_vo.path)
        storage_path: str = req.get("path", "") or ""
        path_only: str = os.path.basename(storage_path) if storage_path else ""
        original_name: str = req.get("name") or path_only
        file_obj = FileDO(
            config_id=req["config_id"],
            name=req.get("name") or path_only,
            original_name=original_name,
            path=path_only,
            storage_path=storage_path,
            url=req["url"],
            type=req.get("type") or "application/octet-stream",
            size=req["size"],
        )
        await self.file_mapper.insert(file_obj)
        return file_obj.id

    async def delete_file(self, file_id):
        row = await self._validate_file_exists(file_id)
        client = await self._get_file_client(row.config_id)
        await client.delete(row.storage_path)
        await self.file_mapper.delete_by_id(file_id)

    async def delete_file_batch(self, ids):
        rows = await self.file_mapper.select_by_ids(ids)
        for row in rows:
            await self.delete_file(row.id)
        return len(rows)

    @override
    async def delete_file_by_storage_path(self, storage_path: str) -> bool:
        """通过存储路径删除文件"""
        if not storage_path:
            return False
        file_obj = await self.file_mapper.select_by_storage_path(storage_path)
        if not file_obj:
            return False
        file_client = await self._get_file_client(file_obj.config_id)
        await file_client.delete(file_obj.storage_path)
        await self.file_mapper.delete_by_id(file_obj.id)
        return True

    @override
    async def get_file_content(self, config_id: int, path: str) -> bytes:
        """获得文件内容"""
        file_client = await self._get_file_client(config_id)
        return await file_client.get_content(path)

    @override
    async def get_file_presigned_url(
        self, name: str, directory: str | None = None
    ) -> FilePresignedUrlRespVO:
        """获取文件预签名上传地址"""
        actual_storage_path = self._generate_upload_path(name, directory)
        file_client = await self._get_master_file_client()
        presigned_dto: FilePresignedUrlRespDTO = await file_client.get_presigned_object_url(
            actual_storage_path
        )
        return FilePresignedUrlRespVO(
            config_id=file_client.get_id(),
            upload_url=presigned_dto.upload_url,
            url=presigned_dto.url,
            path=actual_storage_path,
        )

    @override
    async def create_file_by_vo(self, create_req_vo: FileCreateReqVO) -> int:
        return await self.create_file_record(create_req_vo)

    @override
    async def get_file_count_by_config_id(self, config_id: int) -> int:
        return await self.file_mapper.select_count_by_config_id(config_id)

    @override
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
        file_id, url, _, _ = await self.create_file_full(
            content=content,
            name=name,
            directory=directory,
            type_hint=type_hint,
            path=path,
            config_id=config_id,
        )
        return (file_id, url)

    @override
    async def create_file_full(
        self,
        content: bytes,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> tuple[int, str, int, str]:
        """核心文件创建逻辑：计算类型、生成路径、上传、保存记录，返回完整信息"""
        actual_file_type = type_hint or FileTypeUtils.get_mime_type(content, name)
        base_name_for_db = self._resolve_file_name(name, content, actual_file_type)
        actual_storage_path = AbstractFileClient.key(
            path if path else self._generate_upload_path(base_name_for_db, directory)
        )
        if config_id is not None:
            file_client = await self._get_file_client(config_id)
        else:
            file_client = await self._get_master_file_client()
        url: str = await file_client.upload(
            path=actual_storage_path, content=content, file_type=actual_file_type
        )
        file_obj = FileDO(
            config_id=file_client.get_id(),
            name=base_name_for_db,
            original_name=name or base_name_for_db,
            path=os.path.basename(actual_storage_path),
            storage_path=actual_storage_path,
            url=url,
            type=actual_file_type or "application/octet-stream",
            size=len(content),
        )
        await self.file_mapper.insert(file_obj)
        return (file_obj.id, url, file_obj.config_id, actual_storage_path)

    @override
    async def presign_get_url(self, url: str, expiration_seconds: int | None = None) -> str:
        """生成文件预签名地址，用于读取"""
        if not url:
            raise IllegalArgumentException(msg="URL 不能为空")
        file_obj = await self.file_mapper.select_by_url(url)
        if file_obj is None:
            raise ServiceException(ErrorCodeConstants.FILE_NOT_EXISTS, msg=f"文件不存在: {url}")
        file_client = await self._get_file_client(file_obj.config_id)
        return await file_client.presign_get_url(file_obj.storage_path, expiration_seconds)

    @override
    async def list_objects(
        self, config_id: int, prefix: str, delimiter: str
    ) -> FileListObjectsRespVO:
        """列举指定存储配置下的目录和文件"""
        file_client = await self._get_file_client(config_id)
        raw = await file_client.list_objects(prefix=prefix, delimiter=delimiter)
        objects: list[FileObjectVO] = []
        for d in raw.get("directories", []):
            objects.append(FileObjectVO(key=d["prefix"], name=d["name"], is_directory=True))
        db_files = await self.file_mapper.select_by_config_and_prefix(config_id, prefix)
        db_file_map: dict[str, FileDO] = {}
        for db_f in db_files:
            db_file_map[db_f.storage_path] = db_f
            db_file_map[db_f.path] = db_f
        for f in raw.get("files", []):
            file_key = f["key"]
            file_name = f["name"]
            db_file = db_file_map.get(file_key) or db_file_map.get(file_name)
            file_type = (
                db_file.type if db_file else FileTypeUtils.get_mime_type_from_name(file_name)
            )
            file_url = db_file.url if db_file else self._build_file_url(file_client, file_key)
            objects.append(
                FileObjectVO(
                    key=file_key,
                    name=file_name,
                    size=f.get("size"),
                    last_modified=f.get("lastModified"),
                    type=file_type,
                    is_directory=False,
                    url=file_url,
                )
            )
        return FileListObjectsRespVO(
            objects=objects,
            is_truncated=raw.get("isTruncated", False),
            next_marker=raw.get("nextMarker", ""),
            current_prefix=prefix,
        )

    @override
    async def create_directory(self, config_id: int, directory_path: str) -> None:
        """在指定存储配置下创建目录"""
        if not directory_path:
            raise IllegalArgumentException(msg="目录路径不能为空")
        if not directory_path.endswith("/"):
            directory_path += "/"
        file_client = await self._get_file_client(config_id)
        await file_client.upload(
            path=directory_path, content=b"", file_type="application/x-directory"
        )

    @override
    async def search_files(self, req_vo: FileSearchReqVO) -> PageResult[FileDO]:
        """搜索文件（模糊/前缀），委托给 FileMapper"""
        return await self.file_mapper.search_files(
            config_id=req_vo.config_id,
            keyword=req_vo.keyword,
            search_mode=req_vo.search_mode,
            prefix=req_vo.prefix,
            page_no=req_vo.page,
            page_size=req_vo.page_size,
        )

    @override
    async def delete_by_key(self, config_id: int, key: str) -> None:
        """通过存储配置ID和文件key删除文件或文件夹"""
        file_client = await self._get_file_client(config_id)
        if key.endswith("/"):
            await self._delete_directory_recursive(file_client, config_id, key)
        else:
            await file_client.delete(key)
            db_file = await self.file_mapper.select_by_storage_path(key)
            if db_file and db_file.config_id == config_id:
                await self.file_mapper.delete_by_id(db_file.id)

    @override
    async def delete_by_keys(self, config_id: int, keys: list[str]) -> int:
        """批量通过存储配置ID和文件key删除文件"""
        count = 0
        for key in keys:
            await self.delete_by_key(config_id, key)
            count += 1
        return count

    @override
    async def rename_object(self, config_id: int, old_key: str, new_name: str) -> None:
        """重命名文件或目录"""
        file_client = await self._get_file_client(config_id)
        is_dir = old_key.endswith("/")
        if is_dir:
            trimmed = old_key.rstrip("/")
            parent = trimmed.rsplit("/", 1)[0] + "/" if "/" in trimmed else ""
            new_key = f"{parent}{new_name}/"
        else:
            parent = old_key.rsplit("/", 1)[0] + "/" if "/" in old_key else ""
            new_key = f"{parent}{new_name}"
        if old_key == new_key:
            return
        await file_client.rename(old_key, new_key)
        if is_dir:
            db_files = await self.file_mapper.select_by_config_and_prefix(config_id, old_key)
            for db_file in db_files:
                new_storage_path = new_key + db_file.storage_path[len(old_key) :]
                if db_file.url:
                    db_file.url = db_file.url.replace(db_file.storage_path, new_storage_path)
                db_file.storage_path = new_storage_path
                db_file.path = os.path.basename(new_storage_path.rstrip("/"))
                await self.file_mapper.update_by_id(db_file)
        else:
            db_file = await self.file_mapper.select_by_storage_path(old_key)
            if db_file and db_file.config_id == config_id:
                if db_file.url:
                    db_file.url = db_file.url.replace(old_key, new_key)
                db_file.storage_path = new_key
                db_file.path = os.path.basename(new_key)
                db_file.name = new_name
                await self.file_mapper.update_by_id(db_file)

    async def _validate_file_exists(self, file_id: int) -> FileDO:
        file_obj = await self.file_mapper.select_by_id(file_id)
        if file_obj is None:
            raise ServiceException(ErrorCodeConstants.FILE_NOT_EXISTS)
        return file_obj

    async def _get_file_client(self, config_id: int) -> FileClient:
        """获取指定配置的文件客户端，不存在则抛出异常"""
        file_client = await self.file_config_service.get_file_client(config_id)
        if file_client is None:
            raise ServiceException(
                error_code=ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS,
                msg=f"文件配置({config_id})不存在",
            )
        return file_client

    async def _get_master_file_client(self) -> FileClient:
        """获取主文件客户端，不存在则抛出异常"""
        file_client = await self.file_config_service.get_master_file_client()
        if file_client is None:
            raise ServiceException(
                ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS, msg="文件客户端(master)配置不存在"
            )
        return file_client

    async def _delete_directory_recursive(self, file_client, config_id, prefix):
        prefix = AbstractFileClient.key(prefix)
        raw = await file_client.list_objects(prefix=prefix, delimiter="/")
        if raw["isTruncated"]:
            raise ValueError("目录超过单次列举上限，请分批删除")
        for directory in raw["directories"]:
            await self._delete_directory_recursive(file_client, config_id, directory["prefix"])
        for entry in raw["files"]:
            await file_client.delete(entry["key"])
            await self.file_mapper.soft_delete_by_condition(
                FileDO.config_id == config_id, FileDO.storage_path == entry["key"]
            )
        await file_client.delete(prefix)

    @staticmethod
    def _resolve_file_name(name: str | None, content: bytes, file_type: str | None) -> str:
        """根据原始文件名、内容和MIME类型，生成最终的逻辑文件名"""
        if not name:
            base_name = hashlib.sha256(content).hexdigest()
            extension = FileTypeUtils.get_extension(file_type)
            return f"{base_name}{extension}" if extension else base_name
        if not os.path.splitext(name)[1] and file_type:
            extension = FileTypeUtils.get_extension(file_type)
            if extension:
                return f"{name}{extension}"
        return name

    def _generate_upload_path(self, original_name: str, directory: str | None) -> str:
        """根据配置和输入生成文件上传的完整路径"""
        current_name = original_name
        if self.PATH_SUFFIX_TIMESTAMP_ENABLE:
            main_name, ext_name = os.path.splitext(current_name)
            current_name = f"{main_name}_{int(time.time() * 1000)}{ext_name}"
        path_parts = []
        if directory:
            path_parts.append(directory.rstrip("/"))
        path_parts.append(current_name)
        return "/".join(path_parts)

    @staticmethod
    def _build_file_url(file_client, key):
        if isinstance(file_client, S3FileClient):
            return file_client.domain + "/" + quote(key, safe="/")
        return file_client.format_file_url(file_client.config.domain, key)
