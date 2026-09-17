from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class TenantExportReqVO(TenantPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
