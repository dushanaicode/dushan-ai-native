from __future__ import annotations

import os
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
from module_infra.controller.admin.file.vo.file.file_list_objects_resp_vo import (
    FileListObjectsRespVO,
)
from module_infra.controller.admin.file.vo.file.file_object_vo import FileObjectVO
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.controller.admin.file.vo.file.file_resp_vo import FileRespVO
from module_infra.controller.admin.file.vo.file.file_search_req_vo import FileSearchReqVO
from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.file.file_upload_usage_enum import FileUploadUsageEnum
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.framework.file.core.client.file_client import FileClient
from module_infra.framework.file.core.utils.file_type_utils import FileTypeUtils
from module_infra.service.file.bo.file_content_bo import FileContentBO
from module_infra.service.file.file_config_service import FileConfigService
from module_infra.service.file.file_service import FileService
from module_infra.util.file.file_utils import FileUtils


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
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> str:
        """保存文件并返回访问 URL。config_id 不传则使用 master 配置"""
        _, url = await self.create_file_with_id(
            content=content,
            visibility=visibility,
            name=name,
            directory=directory,
            type_hint=type_hint,
            path=path,
            config_id=config_id,
        )
        return url

    @override
    async def create_business_file(
        self, content: bytes, name: str | None, usage: FileUploadUsageEnum
    ) -> str:
        """按服务端检测的内容类型和用途限制上传。"""
        if not content:
            raise ServiceException(ErrorCodeConstants.FILE_IS_EMPTY)
        if len(content) > usage.max_size:
            raise ServiceException(ErrorCodeConstants.FILE_UPLOAD_SIZE_EXCEEDED)
        mime_type = FileTypeUtils.get_mime_type(content)
        if not usage.allows_mime_type(mime_type):
            raise ServiceException(ErrorCodeConstants.FILE_UPLOAD_TYPE_NOT_ALLOWED)
        return await self.create_file(
            content=content,
            visibility=usage.visibility,
            name=name,
            directory=f"usage/{usage.code}",
            type_hint=mime_type,
        )

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
    async def delete_file_by_storage_path(self, config_id: int, storage_path: str) -> bool:
        """删除指定配置与路径的已登记文件，无元数据时返回 False。"""
        if not storage_path:
            return False
        file_obj = await self.file_mapper.select_by_storage_path(config_id, storage_path)
        if not file_obj:
            return False
        file_client = await self._get_file_client(file_obj.config_id)
        await file_client.delete(file_obj.storage_path)
        await self.file_mapper.delete_by_id(file_obj.id)
        return True

    @override
    async def find_file(
        self, config_id: int, path: str, *, public_only: bool
    ) -> FileContentBO | None:
        """先校验当前租户的记录与可见性，再读取内容；缺失时返回 None。"""
        file_obj = await self.file_mapper.select_by_storage_path(config_id, path)
        if file_obj is None or (
            public_only and file_obj.visibility != FileVisibilityEnum.PUBLIC.code
        ):
            return None
        file_client = await self._get_file_client(config_id)
        try:
            content = await file_client.get_content(path)
        except FileNotFoundError:
            return None
        return FileContentBO(name=file_obj.name, type=file_obj.type, content=content)

    @override
    async def get_file_count_by_config_id(self, config_id: int) -> int:
        return await self.file_mapper.select_count_by_config_id(config_id)

    @override
    async def create_file_with_id(
        self,
        content: bytes,
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> tuple[int, str]:
        """创建文件并返回文件ID和访问URL"""
        file_id, url, _, _ = await self.create_file_full(
            content=content,
            visibility=visibility,
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
        visibility: FileVisibilityEnum,
        name: str | None = None,
        directory: str | None = None,
        type_hint: str | None = None,
        path: str | None = None,
        config_id: int | None = None,
    ) -> tuple[int, str, int, str]:
        """核心文件创建逻辑：计算类型、生成路径、上传、保存记录，返回完整信息"""
        if not content:
            raise ServiceException(ErrorCodeConstants.FILE_IS_EMPTY)
        actual_file_type = type_hint or FileTypeUtils.get_mime_type(content, name)
        base_name_for_db = FileUtils.resolve_file_name(name, content, actual_file_type)
        actual_storage_path = AbstractFileClient.key(
            path
            if path
            else FileUtils.generate_storage_path(
                base_name_for_db, directory, self.PATH_SUFFIX_TIMESTAMP_ENABLE
            )
        )
        if config_id is not None:
            file_client = await self._get_file_client(config_id)
        else:
            file_client = await self._get_master_file_client()
        url: str = await file_client.upload(
            path=actual_storage_path, content=content, file_type=actual_file_type
        )
        if visibility is FileVisibilityEnum.PRIVATE:
            url = self._build_private_file_url(file_client.get_id(), actual_storage_path)
        file_obj = FileDO(
            config_id=file_client.get_id(),
            name=base_name_for_db,
            original_name=name or base_name_for_db,
            path=os.path.basename(actual_storage_path),
            storage_path=actual_storage_path,
            url=url,
            visibility=visibility.code,
            type=actual_file_type,
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
        if file_obj.visibility == FileVisibilityEnum.PRIVATE.code:
            return file_obj.url
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
        db_file_map = {db_file.storage_path: db_file for db_file in db_files}
        for f in raw.get("files", []):
            file_key = f["key"]
            file_name = f["name"]
            db_file = db_file_map.get(file_key)
            file_type = (
                db_file.type if db_file else FileTypeUtils.get_mime_type_from_name(file_name)
            )
            file_url = None
            if db_file is not None:
                file_url = (
                    db_file.url
                    if db_file.visibility == FileVisibilityEnum.PRIVATE.code
                    else await file_client.presign_get_url(file_key)
                )
            objects.append(
                FileObjectVO(
                    key=file_key,
                    name=db_file.name if db_file else file_name,
                    size=f.get("size"),
                    last_modified=f.get("lastModified"),
                    type=file_type,
                    is_directory=False,
                    url=file_url,
                    visibility=db_file.visibility if db_file is not None else None,
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
    async def search_files(self, req_vo: FileSearchReqVO) -> PageResult[FileRespVO]:
        """搜索文件（模糊/前缀），委托给 FileMapper"""
        page = await self.file_mapper.search_files(
            config_id=req_vo.config_id,
            keyword=req_vo.keyword,
            search_mode=req_vo.search_mode,
            prefix=req_vo.prefix,
            page_no=req_vo.page,
            page_size=req_vo.page_size,
        )
        result = page.convert(FileRespVO)
        file_client = await self._get_file_client(req_vo.config_id)
        for item in result.items:
            if item.visibility is FileVisibilityEnum.PUBLIC:
                item.url = await file_client.presign_get_url(item.path)
        return result

    @override
    async def delete_by_key(self, config_id: int, key: str) -> None:
        """通过存储配置ID和文件key删除文件或文件夹"""
        file_client = await self._get_file_client(config_id)
        if key.endswith("/"):
            await self._delete_directory_recursive(file_client, config_id, key)
        else:
            db_file = await self.file_mapper.select_by_storage_path(config_id, key)
            await file_client.delete(key)
            if db_file is not None:
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
        new_key = FileUtils.rename_storage_key(old_key, new_name)
        if old_key == new_key:
            return
        if is_dir:
            db_files = await self.file_mapper.select_by_config_and_prefix(config_id, old_key)
            await file_client.rename(old_key, new_key)
            for db_file in db_files:
                new_storage_path = new_key + db_file.storage_path[len(old_key) :]
                db_file.url = self._renamed_file_url(db_file, new_storage_path)
                db_file.storage_path = new_storage_path
                db_file.path = os.path.basename(new_storage_path.rstrip("/"))
                await self.file_mapper.update_by_id(db_file)
        else:
            db_file = await self.file_mapper.select_by_storage_path(config_id, old_key)
            await file_client.rename(old_key, new_key)
            if db_file is not None:
                db_file.url = self._renamed_file_url(db_file, new_key)
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
    def _build_private_file_url(config_id: int, storage_path: str) -> str:
        return f"/admin-api/infra/file/private/{config_id}/{quote(storage_path, safe='/')}"

    @classmethod
    def _renamed_file_url(cls, file_obj: FileDO, storage_path: str) -> str:
        if file_obj.visibility == FileVisibilityEnum.PRIVATE.code:
            return cls._build_private_file_url(file_obj.config_id, storage_path)
        return file_obj.url.replace(
            quote(file_obj.storage_path, safe="/"), quote(storage_path, safe="/")
        )
