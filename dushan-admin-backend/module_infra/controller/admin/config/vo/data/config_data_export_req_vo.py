from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.config.vo.data.config_data_page_req_vo import ConfigDataPageReqVO


class ConfigDataExportReqVO(ConfigDataPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
