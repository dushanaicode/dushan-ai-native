from framework.common.schemas import BaseVO
from module_system.controller.admin.tenant.vo.tenant.tenant_simple_resp_vo import TenantSimpleRespVO


class AuthTenantConfigRespVO(BaseVO):
    enabled: bool
    tenants: list[TenantSimpleRespVO]
