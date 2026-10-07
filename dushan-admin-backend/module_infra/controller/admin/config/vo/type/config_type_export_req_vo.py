from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.config.vo.type.config_type_page_req_vo import ConfigTypePageReqVO


class ConfigTypeExportReqVO(ConfigTypePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
