from framework.common.schemas.request import ExportFieldsReqVO
from module_system.controller.admin.tenant.vo.packages.packages_package_page_req_vo import (
    TenantPackagePageReqVO,
)


class TenantPackageExportReqVO(TenantPackagePageReqVO, ExportFieldsReqVO):
    """分页筛选条件与导出列选择。"""
