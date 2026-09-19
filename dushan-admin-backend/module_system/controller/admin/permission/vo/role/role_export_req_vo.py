from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.permission.vo.role.role_page_req_vo import RolePageReqVO


class RoleExportReqVO(RolePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
