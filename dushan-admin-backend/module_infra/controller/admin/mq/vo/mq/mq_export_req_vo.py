from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.mq.vo.mq.mq_page_req_vo import MqPageReqVO


class MqExportReqVO(MqPageReqVO, ExportFieldsReqVO):
    """消息定义筛选条件与导出字段。"""
