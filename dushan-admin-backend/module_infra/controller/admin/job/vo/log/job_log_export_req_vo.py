from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.job.vo.log.job_log_page_req_vo import JobLogPageReqVO


class JobLogExportReqVO(JobLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
