import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from framework.common.contracts import SnowflakeIdInput
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.common.schemas.request import IdListReqVO, IdReqVO
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_tenant.public import (
    TenantSettings,
)
from framework.starter_web.public import (
    AccessLogPolicy,
    FileResult,
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.file.vo.file.file_create_directory_req_vo import (
    FileCreateDirectoryReqVO,
)
from module_infra.controller.admin.file.vo.file.file_delete_by_key_req_vo import (
    FileDeleteByKeyReqVO,
)
from module_infra.controller.admin.file.vo.file.file_delete_by_keys_req_vo import (
    FileDeleteByKeysReqVO,
)
from module_infra.controller.admin.file.vo.file.file_list_objects_req_vo import FileListObjectsReqVO
from module_infra.controller.admin.file.vo.file.file_list_objects_resp_vo import (
    FileListObjectsRespVO,
)
from module_infra.controller.admin.file.vo.file.file_page_req_vo import FilePageReqVO
from module_infra.controller.admin.file.vo.file.file_rename_req_vo import FileRenameReqVO
from module_infra.controller.admin.file.vo.file.file_resp_vo import FileRespVO
from module_infra.controller.admin.file.vo.file.file_search_req_vo import FileSearchReqVO
from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.file.file_upload_usage_enum import FileUploadUsageEnum
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum
from module_infra.service.file.file_service import FileService
from module_system.api.auth.workload_api import WorkloadApi

file_controller = APIRouter(prefix="/file", tags=["Infra - 文件存储管理"])
FILE_CACHE_MAX_AGE_SECONDS = 31536000


class FileController:
    @staticmethod
    @file_controller.post(
        "/upload",
        summary="上传文件",
        description="文件管理上传。指定可见性，可选存储配置和目录，不传 configId 则使用主配置",
    )
    @RoutePolicy(
        permissions=("infra:file:upload",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def upload_file(
        file: UploadFile = File(..., description="上传的文件"),
        visibility: FileVisibilityEnum = Form(..., description="可见性"),
        directory: str | None = Form(default=None, description="文件目录"),
        config_id: SnowflakeIdInput | None = Form(
            default=None, alias="configId", description="存储配置ID，不传则使用主配置"
        ),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[str]:
        content = await file.read()
        original_filename = os.path.basename(file.filename or "")
        file_url = await file_service.create_file(
            content=content,
            visibility=visibility,
            name=original_filename,
            directory=directory,
            config_id=config_id,
        )
        return Result.success(data=file_url)

    @staticmethod
    @file_controller.post("/business-upload", summary="业务上传文件")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def business_upload_file(
        file: UploadFile = File(..., description="上传的文件"),
        usage: FileUploadUsageEnum = Form(..., description="上传用途"),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[str]:
        file_url = await file_service.create_business_file(
            content=await file.read(usage.max_size + 1),
            name=os.path.basename(file.filename or ""),
            usage=usage,
        )
        return Result.success(data=file_url)

    @staticmethod
    @file_controller.delete("/delete", summary="删除文件")
    @RoutePolicy(
        permissions=("infra:file:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_file(
        req_vo: IdReqVO = Query(), file_service: FileService = Depends(DiDependency(FileService))
    ) -> Result[bool]:
        await file_service.delete_file(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @file_controller.delete("/delete-list", summary="批量删除文件")
    @RoutePolicy(
        permissions=("infra:file:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_file_batch(
        req_vo: IdListReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[int]:
        deleted_count = await file_service.delete_file_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @file_controller.get("/{config_id}/get/{path:path}", summary="下载文件", response_model=None)
    @RoutePolicy.public()
    @AccessLogPolicy(enabled=False)
    async def get_file_content(
        config_id: SnowflakeIdInput,
        path: str,
        file_service: FileService = Depends(DiDependency(FileService)),
        workloads: WorkloadApi = Depends(DiDependency(WorkloadApi)),
        tenant: TenantSettings = Depends(DiDependency(TenantSettings)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> Response:
        async with workloads.scope("infra.file.read", tenant.default_tenant_id):
            file = await file_service.find_file(config_id, path, public_only=True)
        if file is None:
            raise ServiceException(ErrorCodeConstants.FILE_NOT_EXISTS)
        return files.stream_bytes(
            file.content,
            file.name,
            media_type=file.type,
            disposition="inline",
            cache="public",
            max_age=FILE_CACHE_MAX_AGE_SECONDS,
            immutable=True,
        )

    @staticmethod
    @file_controller.get(
        "/private/{config_id}/{path:path}", summary="读取租户文件", response_model=None
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    @AccessLogPolicy(enabled=False)
    async def get_private_file_content(
        config_id: SnowflakeIdInput,
        path: str,
        file_service: FileService = Depends(DiDependency(FileService)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> Response:
        file = await file_service.find_file(config_id, path, public_only=False)
        if file is None:
            raise ServiceException(ErrorCodeConstants.FILE_NOT_EXISTS)
        return files.stream_bytes(
            file.content,
            file.name,
            media_type=file.type,
            disposition="inline",
            cache="no-store",
        )

    @staticmethod
    @file_controller.get("/page", summary="获得文件分页")
    @RoutePolicy(
        permissions=("infra:file:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_file_page(
        page_req_vo: FilePageReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[PageResult[FileRespVO]]:
        page_result: PageResult[FileDO] = await file_service.get_file_page(page_req_vo)
        resp_vo: PageResult[FileRespVO] = page_result.convert(FileRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @file_controller.get(
        "/list-objects",
        summary="列举目录内容",
        description="列举指定存储配置下的目录和文件，支持前缀导航",
    )
    @RoutePolicy(
        permissions=("infra:file:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def list_objects(
        req_vo: FileListObjectsReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[FileListObjectsRespVO]:
        result = await file_service.list_objects(
            config_id=req_vo.config_id, prefix=req_vo.prefix, delimiter=req_vo.delimiter
        )
        return Result.success(data=result)

    @staticmethod
    @file_controller.post("/create-directory", summary="新建文件夹")
    @RoutePolicy(
        permissions=("infra:file:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_directory(
        req_vo: FileCreateDirectoryReqVO,
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[bool]:
        await file_service.create_directory(
            config_id=req_vo.config_id, directory_path=req_vo.directory_path
        )
        return Result.success(data=True)

    @staticmethod
    @file_controller.get("/search", summary="搜索文件", description="支持模糊搜索和前缀搜索")
    @RoutePolicy(
        permissions=("infra:file:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def search_files(
        req_vo: FileSearchReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[PageResult[FileRespVO]]:
        page_result = await file_service.search_files(req_vo)
        return Result.success(data=page_result)

    @staticmethod
    @file_controller.delete(
        "/delete-by-key",
        summary="通过存储key删除文件或文件夹",
        description="文件浏览器：通过 configId + key 删除文件，如果是目录则递归删除",
    )
    @RoutePolicy(
        permissions=("infra:file:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_by_key(
        req_vo: FileDeleteByKeyReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[bool]:
        await file_service.delete_by_key(config_id=req_vo.config_id, key=req_vo.key)
        return Result.success(data=True)

    @staticmethod
    @file_controller.delete(
        "/delete-by-keys",
        summary="批量通过存储key删除文件",
        description="文件浏览器：通过 configId + keys 批量删除文件",
    )
    @RoutePolicy(
        permissions=("infra:file:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_by_keys(
        req_vo: FileDeleteByKeysReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[int]:
        count = await file_service.delete_by_keys(config_id=req_vo.config_id, keys=req_vo.keys)
        return Result.success(data=count)

    @staticmethod
    @file_controller.post(
        "/rename",
        summary="重命名文件或目录",
        description="文件浏览器：通过 configId + oldKey + newName 重命名文件或目录",
    )
    @RoutePolicy(
        permissions=("infra:file:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def rename_object(
        req_vo: FileRenameReqVO, file_service: FileService = Depends(DiDependency(FileService))
    ) -> Result[bool]:
        await file_service.rename_object(
            config_id=req_vo.config_id, old_key=req_vo.old_key, new_name=req_vo.new_name
        )
        return Result.success(data=True)
