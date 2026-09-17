from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class MailAccountExportReqVO(MailAccountPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
