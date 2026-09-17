from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.schemas.page_result import PageResult
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_web.response.file_result import FileResult
from framework.starter_web.response.result import Result
from framework.starter_web.routing.route_policy import RoutePolicy
from module_system.controller.admin.mail.vo.account.account_export_req_vo import (
    MailAccountExportReqVO,
)
from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO
from module_system.controller.admin.mail.vo.account.account_resp_vo import MailAccountRespVO
from module_system.controller.admin.mail.vo.account.account_save_req_vo import MailAccountSaveReqVO
from module_system.controller.admin.mail.vo.account.account_simple_resp_vo import (
    MailAccountSimpleRespVO,
)
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.service.mail.mail_account_service import MailAccountService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

mail_account_controller = APIRouter(prefix="/mail/account", tags=["System - 邮箱账号管理"])


class MailAccountController:
    @staticmethod
    @mail_account_controller.post("/create", summary="创建邮箱账号")
    @RoutePolicy(
        permissions=("system:mail:account:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_mail_account(
        create_req_vo: MailAccountSaveReqVO,
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[SnowflakeIdStr]:
        account_id = await mail_account_service.create_mail_account(create_req_vo)
        return Result.success(data=account_id)

    @staticmethod
    @mail_account_controller.put("/update", summary="修改邮箱账号")
    @RoutePolicy(
        permissions=("system:mail:account:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_mail_account(
        update_req_vo: MailAccountSaveReqVO,
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[bool]:
        await mail_account_service.update_mail_account(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @mail_account_controller.delete("/delete", summary="删除邮箱账号")
    @RoutePolicy(
        permissions=("system:mail:account:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_mail_account(
        req_vo: IdReqVO = Query(),
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[bool]:
        await mail_account_service.delete_mail_account(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @mail_account_controller.delete("/delete-list", summary="批量删除邮箱账号")
    @RoutePolicy(
        permissions=("system:mail:account:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_mail_account_batch(
        req_vo: IdListReqVO = Query(),
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[int]:
        deleted_count = await mail_account_service.delete_mail_account_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @mail_account_controller.get("/get", summary="获得邮箱账号")
    @RoutePolicy(
        permissions=("system:mail:account:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_mail_account(
        req_vo: IdReqVO = Query(),
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[MailAccountRespVO]:
        account = await mail_account_service.get_mail_account(req_vo.id)
        resp = MailAccountRespVO.model_validate(account)
        return Result.success(data=resp)

    @staticmethod
    @mail_account_controller.get("/page", summary="获得邮箱账号分页")
    @RoutePolicy(
        permissions=("system:mail:account:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_mail_account_page(
        page_req_vo: MailAccountPageReqVO = Query(),
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[PageResult[MailAccountRespVO]]:
        page_result: PageResult[MailAccountDO] = await mail_account_service.get_mail_account_page(
            page_req_vo
        )
        resp_vo: PageResult[MailAccountRespVO] = page_result.convert(MailAccountRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @mail_account_controller.get("/export-fields", summary="获取邮箱账号可导出字段列表")
    @RoutePolicy(
        permissions=("system:mail:account:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_mail_account_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(MailAccountRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @mail_account_controller.get(
        "/export-excel", summary="导出邮箱账号", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:mail:account:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_mail_account_list(
        page_req_vo: MailAccountExportReqVO = Query(),
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
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
        page_result: PageResult[MailAccountDO] = await mail_account_service.get_mail_account_page(
            page_req_vo
        )
        list_data = page_result.items
        resp_list: list[MailAccountRespVO] = [
            MailAccountRespVO.model_validate(item) for item in list_data
        ]
        filename = "邮箱账号数据"
        file_data = await excel_writer.write(
            "数据",
            MailAccountRespVO,
            resp_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @mail_account_controller.get("/simple-list", summary="获得邮箱账号精简列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_mail_account_list(
        mail_account_service: MailAccountService = Depends(DiDependency(MailAccountService)),
    ) -> Result[list[MailAccountSimpleRespVO]]:
        accounts = await mail_account_service.get_mail_account_list()
        simple_list = [MailAccountSimpleRespVO.model_validate(item) for item in accounts]
        return Result.success(data=simple_list)
