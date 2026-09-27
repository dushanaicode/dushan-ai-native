from framework.common.schemas.request import ExportFieldsReqVO
from module_infra.controller.admin.data_source.vo.data_source_config_page_req_vo import (
    DataSourceConfigPageReqVO,
)


class DataSourceConfigExportReqVO(DataSourceConfigPageReqVO, ExportFieldsReqVO):
    """数据源筛选条件与导出字段。"""
