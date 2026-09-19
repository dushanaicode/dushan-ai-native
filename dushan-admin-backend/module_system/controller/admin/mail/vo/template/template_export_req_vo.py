from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.mail.vo.template.template_page_req_vo import (
    MailTemplatePageReqVO,
)


class MailTemplateExportReqVO(MailTemplatePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
