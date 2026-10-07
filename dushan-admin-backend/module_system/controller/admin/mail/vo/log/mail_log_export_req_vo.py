from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.mail.vo.log.mail_log_page_req_vo import MailLogPageReqVO


class MailLogExportReqVO(MailLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
