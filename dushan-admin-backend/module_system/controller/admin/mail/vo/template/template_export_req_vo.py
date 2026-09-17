from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class MailTemplateExportReqVO(MailTemplatePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
