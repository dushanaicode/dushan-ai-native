from module_system.controller.admin.dict.vo.data.data_page_req_vo import DictDataPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class DictDataExportReqVO(DictDataPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
