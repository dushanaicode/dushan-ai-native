from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.mq.vo.log.mq_log_page_req_vo import MqLogPageReqVO


class MqLogExportReqVO(MqLogPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
