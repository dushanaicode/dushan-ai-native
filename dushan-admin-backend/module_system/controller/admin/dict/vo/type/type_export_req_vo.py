from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.dict.vo.type.type_page_req_vo import DictTypePageReqVO


class DictTypeExportReqVO(DictTypePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
