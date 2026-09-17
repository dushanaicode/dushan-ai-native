from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_page_req_vo import (
    OperateLogPageReqVO,
)
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class OperateLogExportReqVO(OperateLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
