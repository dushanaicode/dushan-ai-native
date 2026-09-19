from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts import SnowflakeIdStr
from framework.common.page import PageResult, PageSettings
from framework.common.schemas.request import IdListReqVO, IdReqVO, UpdateStatusReqVO
from framework.starter_di.public import (
    DiDependency,
)
from framework.starter_excel.public import (
    DictDataProvider,
    ExcelProviders,
    ExcelWriter,
)
from framework.starter_security.public import (
    SecurityContext,
    SecurityRealm,
)
from framework.starter_web.public import (
    FileResult,
    Result,
    RoutePolicy,
)
from module_system.controller.admin.mail.vo.template.template_export_req_vo import (
    MailTemplateExportReqVO,
)
from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)
from module_system.controller.admin.mail.vo.template.template_resp_vo import MailTemplateRespVO
from module_system.controller.admin.mail.vo.template.template_save_req_vo import (
    MailTemplateSaveReqVO,
)
from module_system.controller.admin.mail.vo.template.template_send_req_vo import (
    MailTemplateSendReqVO,
)
from module_system.controller.admin.mail.vo.template.template_simple_resp_vo import (
    MailTemplateSimpleRespVO,
)
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO
from module_system.service.mail.mail_send_service import MailSendService
from module_system.service.mail.mail_template_service import MailTemplateService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

mail_template_controller = APIRouter(prefix="/mail/template", tags=["System - 邮件模版管理"])


class MailTemplateController:
    @staticmethod
    @mail_template_controller.post("/create", summary="创建邮件模版")
    @RoutePolicy(
        permissions=("system:mail:template:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_mail_template(
        create_req_vo: MailTemplateSaveReqVO,
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[SnowflakeIdStr]:
        template_id = await mail_template_service.create_mail_template(create_req_vo)
        return Result.success(data=template_id)

    @staticmethod
    @mail_template_controller.put("/update", summary="修改邮件模版")
    @RoutePolicy(
        permissions=("system:mail:template:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_mail_template(
        update_req_vo: MailTemplateSaveReqVO,
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[bool]:
        await mail_template_service.update_mail_template(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @mail_template_controller.put("/update-status", summary="修改邮件模板状态")
    @RoutePolicy(
        permissions=("system:mail:template:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @mail_template_controller.delete("/delete", summary="删除邮件模版")
    @RoutePolicy(
        permissions=("system:mail:template:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_mail_template(
        req_vo: IdReqVO = Query(),
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[bool]:
        await mail_template_service.delete_mail_template(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @mail_template_controller.delete("/delete-list", summary="批量删除邮件模板")
    @RoutePolicy(
        permissions=("system:mail:template:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_mail_template_batch(
        req_vo: IdListReqVO = Query(),
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[int]:
        deleted_count = await mail_template_service.delete_mail_template_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @mail_template_controller.get("/get", summary="获得邮件模版")
    @RoutePolicy(
        permissions=("system:mail:template:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_mail_template(
        req_vo: IdReqVO = Query(),
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[MailTemplateRespVO]:
        template = await mail_template_service.get_mail_template(req_vo.id)
        data = MailTemplateRespVO.model_validate(template)
        return Result.success(data=data)

    @staticmethod
    @mail_template_controller.get("/page", summary="获得邮件模版分页")
    @RoutePolicy(
        permissions=("system:mail:template:query",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_mail_template_page(
        page_req_vo: MailTemplatePageReqVO = Query(),
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[PageResult[MailTemplateRespVO]]:
        page_result: PageResult[
            MailTemplateDO
        ] = await mail_template_service.get_mail_template_page(page_req_vo)
        resp_vo: PageResult[MailTemplateRespVO] = page_result.convert(MailTemplateRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @mail_template_controller.get("/export-fields", summary="获取邮件模版可导出字段列表")
    @RoutePolicy(
        permissions=("system:mail:template:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_mail_template_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(MailTemplateRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @mail_template_controller.get(
        "/export-excel", summary="导出邮件模版", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:mail:template:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_mail_template_list(
        page_req_vo: MailTemplateExportReqVO = Query(),
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
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
        page_result: PageResult[
            MailTemplateDO
        ] = await mail_template_service.get_mail_template_page(page_req_vo)
        list_data = page_result.items
        resp_list: list[MailTemplateRespVO] = [
            MailTemplateRespVO.model_validate(item) for item in list_data
        ]
        filename = "邮件模版数据"
        file_data = await excel_writer.write(
            "数据",
            MailTemplateRespVO,
            resp_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @mail_template_controller.get("/simple-list", summary="获得邮件模版精简列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_template_list(
        mail_template_service: MailTemplateService = Depends(DiDependency(MailTemplateService)),
    ) -> Result[list[MailTemplateSimpleRespVO]]:
        templates = await mail_template_service.get_mail_template_list()
        data = [MailTemplateSimpleRespVO.model_validate(item) for item in templates]
        return Result.success(data=data)

    @staticmethod
    @mail_template_controller.post("/send-mail", summary="发送邮件")
    @RoutePolicy(
        permissions=("system:mail:template:send-mail",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def send_mail(
        send_req_vo: MailTemplateSendReqVO,
        mail_send_service: MailSendService = Depends(DiDependency(MailSendService)),
        security: SecurityContext = Depends(DiDependency(SecurityContext)),
    ) -> Result[SnowflakeIdStr]:
        user_id = int(security.require().account_id)
        send_log_id = await mail_send_service.send_multiple_mail_to_admin(
            MailBatchSendBO(**send_req_vo.model_dump(by_alias=False), user_id=user_id)
        )
        return Result.success(data=send_log_id)
