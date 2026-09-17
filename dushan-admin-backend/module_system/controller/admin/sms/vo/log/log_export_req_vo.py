from module_system.controller.admin.sms.vo.log.log_page_req_vo import SmsLogPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class SmsLogExportReqVO(SmsLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
