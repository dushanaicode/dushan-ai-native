from module_system.controller.admin.logger.vo.loginlog.loginlog_login_log_page_req_vo import (
    LoginLogPageReqVO,
)
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class LoginLogExportReqVO(LoginLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
