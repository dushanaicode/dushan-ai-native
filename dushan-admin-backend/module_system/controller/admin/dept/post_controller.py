from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.enums.status_enum import StatusEnum
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.common.utils.collection.conversion_utils import ConversionUtils
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.dept.vo.post.post_export_req_vo import PostExportReqVO
from module_system.controller.admin.dept.vo.post.post_page_req_vo import PostPageReqVO
from module_system.controller.admin.dept.vo.post.post_resp_vo import PostRespVO
from module_system.controller.admin.dept.vo.post.post_save_req_vo import PostSaveReqVO
from module_system.controller.admin.dept.vo.post.post_simple_resp_vo import PostSimpleRespVO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.definitions.vo.update_status_req_vo import UpdateStatusReqVO
from module_system.service.dept.post_service import PostService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

post_controller = APIRouter(prefix="/dept/post", tags=["System - 岗位管理"])


class PostController:
    @staticmethod
    @post_controller.post("/create", summary="创建岗位")
    @RoutePolicy(
        permissions=("system:dept:post:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_post(
        create_req_vo: PostSaveReqVO,
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[SnowflakeIdStr]:
        id = await post_service.create_post(create_req_vo)
        return Result.success(data=id)

    @staticmethod
    @post_controller.put("/update", summary="修改岗位")
    @RoutePolicy(
        permissions=("system:dept:post:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_post(
        update_req_vo: PostSaveReqVO,
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[bool]:
        await post_service.update_post(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @post_controller.put("/update-status", summary="修改岗位状态")
    @RoutePolicy(
        permissions=("system:dept:post:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_post_status(
        req_vo: UpdateStatusReqVO,
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[bool]:
        await post_service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @post_controller.delete("/delete", summary="删除岗位")
    @RoutePolicy(
        permissions=("system:dept:post:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_post(
        req_vo: IdReqVO = Query(),
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[bool]:
        await post_service.delete_post(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @post_controller.delete("/delete-list", summary="批量删除岗位")
    @RoutePolicy(
        permissions=("system:dept:post:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_post_batch(
        req_vo: IdListReqVO = Query(),
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[int]:
        deleted_count = await post_service.delete_post_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @post_controller.get("/get", summary="获得岗位信息")
    @RoutePolicy(
        permissions=("system:dept:post:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_post(
        req_vo: IdReqVO = Query(),
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[PostRespVO]:
        post = await post_service.get_post(req_vo.id)
        return Result.success(data=PostRespVO.model_validate(post))

    @staticmethod
    @post_controller.get("/simple-list", summary="获取岗位全列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_post_list(
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[list[PostSimpleRespVO]]:
        posts = await post_service.get_post_list(None, [StatusEnum.ENABLE.code])
        posts = sorted(posts, key=lambda x: x.sort)
        return Result.success(data=[PostSimpleRespVO.model_validate(post) for post in posts])

    @staticmethod
    @post_controller.get("/page", summary="获得岗位分页列表")
    @RoutePolicy(
        permissions=("system:dept:post:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_post_page(
        page_req_vo: PostPageReqVO = Query(),
        post_service: PostService = Depends(DiDependency(PostService)),
    ) -> Result[PageResult[PostRespVO]]:
        page_result: PageResult[PostDO] = await post_service.get_post_page(page_req_vo)
        resp_vo: PageResult[PostRespVO] = page_result.convert(PostRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @post_controller.get("/export-fields", summary="获取岗位可导出字段列表")
    @RoutePolicy(
        permissions=("system:dept:post:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_export_post_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(PostRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @post_controller.get("/export-excel", summary="导出岗位", response_class=StreamingResponse)
    @RoutePolicy(
        permissions=("system:dept:post:export",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def export_post(
        page_req_vo: PostExportReqVO = Query(),
        post_service: PostService = Depends(DiDependency(PostService)),
        excel_writer: ExcelWriter = Depends(DiDependency(ExcelWriter)),
        files: FileResult = Depends(DiDependency(FileResult)),
        dictionaries: DictDataProvider = Depends(DiDependency(DictDataProvider)),
        departments: DeptInfoProviderAdapter = Depends(DiDependency(DeptInfoProviderAdapter)),
        posts: PostInfoProviderAdapter = Depends(DiDependency(PostInfoProviderAdapter)),
        page_settings: PageSettings = Depends(DiDependency(PageSettings)),
    ) -> StreamingResponse:
        excel_providers = ExcelProviders(
            dictionaries=dictionaries, departments=departments, posts=posts
        )
        page_req_vo.enable_fetch_all(
            max_rows=min(excel_writer.settings.max_export_rows, page_settings.fetch_all_max_rows)
        )
        page_result: PageResult[PostDO] = await post_service.get_post_page(page_req_vo)
        excel_list: list[PostRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, PostRespVO
        )
        filename = "岗位数据"
        file_data = await excel_writer.write(
            "数据", PostRespVO, excel_list, providers=excel_providers, fields=page_req_vo.fields
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")
