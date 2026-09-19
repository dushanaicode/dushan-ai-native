from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO


class SmsLogExportReqVO(SmsLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
