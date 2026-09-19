from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.mail.vo.account.account_page_req_vo import MailAccountPageReqVO


class MailAccountExportReqVO(MailAccountPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
