from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdInput, SnowflakeIdStr
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from framework.starter_web.utils.request_utils import RequestUtils
from module_infra.controller.admin.codegen.vo.codegen_column_resp_vo import CodegenColumnRespVO
from module_infra.controller.admin.codegen.vo.codegen_create_list_req_vo import (
    CodegenCreateListReqVO,
)
from module_infra.controller.admin.codegen.vo.codegen_database_table_resp_vo import (
    DatabaseTableRespVO,
)
from module_infra.controller.admin.codegen.vo.codegen_detail_resp_vo import CodegenDetailRespVO
from module_infra.controller.admin.codegen.vo.codegen_preview_resp_vo import CodegenPreviewRespVO
from module_infra.controller.admin.codegen.vo.codegen_table_page_req_vo import CodegenTablePageReqVO
from module_infra.controller.admin.codegen.vo.codegen_table_resp_vo import CodegenTableRespVO
from module_infra.controller.admin.codegen.vo.codegen_update_req_vo import CodegenUpdateReqVO
from module_infra.controller.common.vo.id_req_vo import IdReqVO
from module_infra.dal.dataobject.codegen.codegen_table_do import CodegenTableDO
from module_infra.service.codegen.codegen_service import CodegenService

codegen_controller = APIRouter(prefix="/codegen", tags=["Infra - 代码生成"])


class CodegenController:
    @staticmethod
    @codegen_controller.post("/create-list", summary="批量导入数据库表")
    @RoutePolicy(
        permissions=("infra:codegen:create",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def create_codegen_list(
        req_vo: CodegenCreateListReqVO,
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[list[SnowflakeIdStr]]:
        table_ids = await codegen_service.create_codegen_list(req_vo)
        return Result.success(data=table_ids)

    @staticmethod
    @codegen_controller.put("/update", summary="更新代码生成配置")
    @RoutePolicy(
        permissions=("infra:codegen:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def update_codegen_table(
        req_vo: CodegenUpdateReqVO,
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[bool]:
        await codegen_service.update_codegen_table(req_vo)
        return Result.success(data=True)

    @staticmethod
    @codegen_controller.delete("/delete", summary="删除代码生成表")
    @RoutePolicy(
        permissions=("infra:codegen:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_codegen_table(
        req_vo: IdReqVO = Query(),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[bool]:
        await codegen_service.delete_codegen_table(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @codegen_controller.delete("/delete-list", summary="批量删除代码生成表")
    @RoutePolicy(
        permissions=("infra:codegen:delete",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def delete_codegen_table_list(
        req_vo: IdListReqVO = Query(),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[bool]:
        await codegen_service.delete_codegen_table_list(req_vo.ids)
        return Result.success(data=True)

    @staticmethod
    @codegen_controller.get("/table/page", summary="获得代码生成表分页")
    @RoutePolicy(
        permissions=("infra:codegen:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_codegen_table_page(
        request: Request, codegen_service: CodegenService = Depends(DiDependency(CodegenService))
    ) -> Result[PageResult[CodegenTableRespVO]]:
        page_req_vo = RequestUtils.validate_with_auto_list_params(request, CodegenTablePageReqVO)
        page_result: PageResult[CodegenTableDO] = await codegen_service.get_codegen_table_page(
            page_req_vo
        )
        resp_vo: PageResult[CodegenTableRespVO] = page_result.convert(CodegenTableRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @codegen_controller.get("/detail", summary="获得代码生成详情")
    @RoutePolicy(
        permissions=("infra:codegen:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_codegen_detail(
        table_id: SnowflakeIdInput = Query(..., alias="tableId", description="表编号"),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[CodegenDetailRespVO]:
        detail = await codegen_service.get_codegen_detail(table_id)
        table_resp = CodegenTableRespVO.model_validate(detail["table"])
        column_resp_list = [CodegenColumnRespVO.model_validate(c) for c in detail["columns"]]
        return Result.success(data=CodegenDetailRespVO(table=table_resp, columns=column_resp_list))

    @staticmethod
    @codegen_controller.get("/table/list", summary="获得代码生成表列表")
    @RoutePolicy(
        permissions=("infra:codegen:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_codegen_table_list(
        data_source_config_id: SnowflakeIdInput = Query(
            ..., alias="dataSourceConfigId", description="数据源配置编号"
        ),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[list[CodegenTableRespVO]]:
        tables = await codegen_service.get_codegen_table_list(data_source_config_id)
        resp_list = [CodegenTableRespVO.model_validate(t) for t in tables]
        return Result.success(data=resp_list)

    @staticmethod
    @codegen_controller.get("/db/table/list", summary="获取数据库的表列表")
    @RoutePolicy(
        permissions=("infra:codegen:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_schema_table_list(
        data_source_config_id: SnowflakeIdInput = Query(
            ..., alias="dataSourceConfigId", description="数据源配置编号"
        ),
        table_name: str | None = Query(None, alias="tableName", description="表名称"),
        table_comment: str | None = Query(None, alias="tableComment", description="表描述"),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[list[DatabaseTableRespVO]]:
        result = await codegen_service.get_schema_table_list(
            data_source_config_id, table_name, table_comment
        )
        return Result.success(data=result)

    @staticmethod
    @codegen_controller.put("/sync-from-db", summary="从数据库同步表结构")
    @RoutePolicy(
        permissions=("infra:codegen:update",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def sync_codegen_from_db(
        table_id: SnowflakeIdInput = Query(..., alias="tableId", description="表编号"),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[bool]:
        await codegen_service.sync_codegen_from_db(table_id)
        return Result.success(data=True)

    @staticmethod
    @codegen_controller.get("/preview", summary="预览代码")
    @RoutePolicy(
        permissions=("infra:codegen:preview",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def preview_codegen(
        table_id: SnowflakeIdInput = Query(..., alias="tableId", description="表编号"),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
    ) -> Result[list[CodegenPreviewRespVO]]:
        result = await codegen_service.preview_codegen(table_id)
        return Result.success(data=result)

    @staticmethod
    @codegen_controller.get("/download", summary="下载代码", response_class=StreamingResponse)
    @RoutePolicy(
        permissions=("infra:codegen:download",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def download_codegen(
        table_id: SnowflakeIdInput = Query(..., alias="tableId", description="表编号"),
        codegen_service: CodegenService = Depends(DiDependency(CodegenService)),
        files: FileResult = Depends(DiDependency(FileResult)),
    ) -> StreamingResponse:
        zip_bytes = await codegen_service.download_codegen(table_id)
        return files.stream_bytes(
            zip_bytes, f"codegen-{table_id}.zip", media_type="application/zip"
        )
