from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.logger.vo.api_access_log.api_access_log_page_req_vo import (
    ApiAccessLogPageReqVO,
)


class ApiAccessLogExportReqVO(ApiAccessLogPageReqVO, ExportFieldsReqVO):
    """访问日志筛选条件与导出字段。"""
