from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile

from framework.common.contracts import SnowflakeIdStr
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_security.public import (
    SecurityRealm,
)
from framework.starter_web.public import (
    Result,
    RoutePolicy,
)
from module_infra.controller.admin.file.vo.file.file_create_req_vo import FileCreateReqVO
from module_infra.controller.admin.file.vo.file.file_presigned_url_resp_vo import (
    FilePresignedUrlRespVO,
)
from module_infra.controller.weapp.file.vo.file_weapp_file_presigned_url_req_vo import (
    WeappFilePresignedUrlReqVO,
)
from module_infra.service.file.file_service import FileService

weapp_file_controller = APIRouter(prefix="/file", tags=["用户 WeApp - 文件存储"])


class FileWeappFileController:
    @staticmethod
    @weapp_file_controller.post("/upload", summary="上传文件")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def upload_file(
        file: UploadFile = File(..., description="文件附件"),
        directory: str | None = Form(None, description="文件目录", examples=["XXX/YYY"]),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[str]:
        content = await file.read()
        filename = file.filename
        content_type = file.content_type
        file_id = await file_service.create_file(
            content=content, name=filename, directory=directory, type_hint=content_type
        )
        return Result.success(data=file_id)

    @staticmethod
    @weapp_file_controller.get(
        "/presigned-url",
        summary="获取文件预签名地址",
        description="模式二：前端上传文件：用于前端直接上传七牛、阿里云 OSS 等文件存储器",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_file_presigned_url(
        req_vo: WeappFilePresignedUrlReqVO = Query(),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[FilePresignedUrlRespVO]:
        presigned_url_resp = await file_service.get_file_presigned_url(
            req_vo.name, req_vo.directory
        )
        return Result.success(data=presigned_url_resp)

    @staticmethod
    @weapp_file_controller.post(
        "/create",
        summary="创建文件",
        description="模式二：前端上传文件：配合 presigned-url 接口，记录上传了上传的文件",
    )
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def create_file(
        create_req_vo: FileCreateReqVO = Body(...),
        file_service: FileService = Depends(DiDependency(FileService)),
    ) -> Result[SnowflakeIdStr]:
        file_id = await file_service.create_file_by_vo(create_req_vo)
        return Result.success(data=file_id)
