from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.dict.vo.data.data_page_req_vo import DictDataPageReqVO


class DictDataExportReqVO(DictDataPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
