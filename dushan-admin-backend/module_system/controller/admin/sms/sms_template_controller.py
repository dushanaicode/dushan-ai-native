from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from framework.common.contracts.snowflake_id import SnowflakeIdStr
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
from module_system.controller.admin.sms.vo.template.template_export_req_vo import (
    SmsTemplateExportReqVO,
)
from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO
from module_system.controller.admin.sms.vo.template.template_resp_vo import SmsTemplateRespVO
from module_system.controller.admin.sms.vo.template.template_save_req_vo import SmsTemplateSaveReqVO
from module_system.controller.admin.sms.vo.template.template_send_req_vo import SmsTemplateSendReqVO
from module_system.controller.admin.sms.vo.template.template_simple_resp_vo import (
    SmsTemplateSimpleRespVO,
)
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO
from module_system.definitions.vo.id_req_vo import IdReqVO
from module_system.definitions.vo.update_status_req_vo import UpdateStatusReqVO
from module_system.service.sms.bo.sms_send_bo import SmsSendBO
from module_system.service.sms.sms_send_service import SmsSendService
from module_system.service.sms.sms_template_service import SmsTemplateService
from module_system.spi.dept.dept_info_provider_adapter import DeptInfoProviderAdapter
from module_system.spi.dept.post_info_provider_adapter import PostInfoProviderAdapter

sms_template_controller = APIRouter(prefix="/sms/template", tags=["System - 短信模版管理"])


class SmsTemplateController:
    @staticmethod
    @sms_template_controller.post("/create", summary="创建短信模板")
    @RoutePolicy(
        permissions=("system:sms:template:create",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def create_sms_template(
        create_req_vo: SmsTemplateSaveReqVO,
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[SnowflakeIdStr]:
        template_id = await sms_template_service.create_sms_template(create_req_vo)
        return Result.success(data=template_id)

    @staticmethod
    @sms_template_controller.put("/update", summary="更新短信模板")
    @RoutePolicy(
        permissions=("system:sms:template:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_sms_template(
        update_req_vo: SmsTemplateSaveReqVO,
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[bool]:
        await sms_template_service.update_sms_template(update_req_vo)
        return Result.success(data=True)

    @staticmethod
    @sms_template_controller.put("/update-status", summary="修改短信模板状态")
    @RoutePolicy(
        permissions=("system:sms:template:update",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def update_status(
        req_vo: UpdateStatusReqVO,
        service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[bool]:
        await service.update_status(req_vo.id, req_vo.status)
        return Result.success(data=True)

    @staticmethod
    @sms_template_controller.delete("/delete", summary="删除短信模板")
    @RoutePolicy(
        permissions=("system:sms:template:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_sms_template(
        req_vo: IdReqVO = Query(),
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[bool]:
        await sms_template_service.delete_sms_template(req_vo.id)
        return Result.success(data=True)

    @staticmethod
    @sms_template_controller.delete("/delete-list", summary="批量删除短信模板")
    @RoutePolicy(
        permissions=("system:sms:template:delete",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def delete_sms_template_batch(
        req_vo: IdListReqVO = Query(),
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[int]:
        deleted_count = await sms_template_service.delete_sms_template_batch(req_vo.ids)
        return Result.success(data=deleted_count)

    @staticmethod
    @sms_template_controller.get("/get", summary="获得短信模板")
    @RoutePolicy(
        permissions=("system:sms:template:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_sms_template(
        req_vo: IdReqVO = Query(),
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[SmsTemplateRespVO]:
        template = await sms_template_service.get_sms_template(req_vo.id)
        if template is None:
            return Result.success(data=None)
        data = SmsTemplateRespVO.model_validate(template)
        return Result.success(data=data)

    @staticmethod
    @sms_template_controller.get("/page", summary="获得短信模板分页")
    @RoutePolicy(
        permissions=("system:sms:template:query",), tenant_required=True, realm=SecurityRealm.TENANT
    )
    async def get_sms_template_page(
        page_req_vo: SmsTemplatePageReqVO = Query(),
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[PageResult[SmsTemplateRespVO]]:
        page_result: PageResult[SmsTemplateDO] = await sms_template_service.get_sms_template_page(
            page_req_vo
        )
        resp_vo: PageResult[SmsTemplateRespVO] = page_result.convert(SmsTemplateRespVO)
        return Result.success(data=resp_vo)

    @staticmethod
    @sms_template_controller.get("/export-fields", summary="获取短信模板可导出字段列表")
    @RoutePolicy(
        permissions=("system:sms:template:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def get_export_sms_template_fields() -> Result[list[dict[str, str]]]:
        export_fields = ExcelWriter.export_fields(SmsTemplateRespVO)
        return Result.success(data=export_fields)

    @staticmethod
    @sms_template_controller.get(
        "/export-excel", summary="导出短信模板 Excel", response_class=StreamingResponse
    )
    @RoutePolicy(
        permissions=("system:sms:template:export",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def export_sms_template_excel(
        page_req_vo: SmsTemplateExportReqVO = Query(),
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
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
        page_result: PageResult[SmsTemplateDO] = await sms_template_service.get_sms_template_page(
            page_req_vo
        )
        excel_list: list[SmsTemplateRespVO] = ConversionUtils.list_to_vo_list(
            page_result.items, SmsTemplateRespVO
        )
        filename = "短信模板"
        file_data = await excel_writer.write(
            "数据",
            SmsTemplateRespVO,
            excel_list,
            providers=excel_providers,
            fields=page_req_vo.fields,
        )
        return files.excel_stream(file_data, file_name=f"{filename}.xlsx")

    @staticmethod
    @sms_template_controller.get("/simple-list", summary="获得短信模板精简列表")
    @RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT)
    async def get_simple_sms_template_list(
        sms_template_service: SmsTemplateService = Depends(DiDependency(SmsTemplateService)),
    ) -> Result[list[SmsTemplateSimpleRespVO]]:
        templates = await sms_template_service.get_sms_template_list()
        simple_list = [SmsTemplateSimpleRespVO.model_validate(item) for item in templates]
        return Result.success(data=simple_list)

    @staticmethod
    @sms_template_controller.post("/send-sms", summary="发送短信")
    @RoutePolicy(
        permissions=("system:sms:template:send-sms",),
        tenant_required=True,
        realm=SecurityRealm.TENANT,
    )
    async def send_sms(
        send_req_vo: SmsTemplateSendReqVO,
        sms_send_service: SmsSendService = Depends(DiDependency(SmsSendService)),
    ) -> Result[SnowflakeIdStr]:
        log_id = await sms_send_service.send_single_sms_to_admin(
            SmsSendBO(
                mobile=send_req_vo.mobile,
                user_id=None,
                template_code=send_req_vo.template_code,
                template_params=send_req_vo.template_params,
            )
        )
        return Result.success(data=log_id)
