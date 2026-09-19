from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.tenant.vo.tenant.tenant_page_req_vo import TenantPageReqVO


class TenantExportReqVO(TenantPageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
