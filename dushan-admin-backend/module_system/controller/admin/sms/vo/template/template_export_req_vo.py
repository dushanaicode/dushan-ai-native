from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO


class SmsTemplateExportReqVO(SmsTemplatePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
