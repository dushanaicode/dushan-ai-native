from module_system.controller.admin.sms.vo.template.template_page_req_vo import SmsTemplatePageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class SmsTemplateExportReqVO(SmsTemplatePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
