from module_system.controller.admin.mail.vo.log.log_page_req_vo import MailLogPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class MailLogExportReqVO(MailLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
