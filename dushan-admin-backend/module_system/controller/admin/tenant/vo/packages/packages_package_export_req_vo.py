from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)
from module_system.definitions.vo.export_fields_req_vo import ExportFieldsReqVO


class TenantPackageExportReqVO(TenantPackagePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
