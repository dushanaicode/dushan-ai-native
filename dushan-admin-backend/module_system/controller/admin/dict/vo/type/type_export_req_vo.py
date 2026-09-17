from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class DictTypeExportReqVO(DictTypePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
