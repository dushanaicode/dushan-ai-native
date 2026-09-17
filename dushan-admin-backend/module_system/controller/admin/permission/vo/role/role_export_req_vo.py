from module_system.controller.admin.permission.vo.role.role_page_req_vo import RolePageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class RoleExportReqVO(RolePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
