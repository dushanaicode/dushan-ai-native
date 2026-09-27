from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.job.vo.job.job_page_req_vo import JobPageReqVO


class JobExportReqVO(JobPageReqVO, ExportFieldsReqVO):
    """任务筛选条件与导出字段。"""
