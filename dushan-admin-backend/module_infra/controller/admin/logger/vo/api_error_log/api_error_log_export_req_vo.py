from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.logger.vo.api_error_log.api_error_log_page_req_vo import (
    ApiErrorLogPageReqVO,
)


class ApiErrorLogExportReqVO(ApiErrorLogPageReqVO, ExportFieldsReqVO):
    """错误日志筛选条件与导出字段。"""
