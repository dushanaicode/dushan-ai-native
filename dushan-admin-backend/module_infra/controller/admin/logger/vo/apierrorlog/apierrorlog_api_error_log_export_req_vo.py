from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.logger.vo.apierrorlog.apierrorlog_api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)


class ApiErrorLogExportReqVO(ApiErrorLogPageReqVO, ExportFieldsReqVO):
    """错误日志筛选条件与导出字段。"""
