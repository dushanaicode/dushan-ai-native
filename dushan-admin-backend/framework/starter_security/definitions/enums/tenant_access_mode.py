from framework.common.enums.base_enum import BaseEnum


class TenantAccessMode(BaseEnum):
    """可信租户身份的权限来源，由 Security/Web/Tenant 共用。"""

    DIRECT_MEMBERSHIP = ("direct_membership", "直属成员")
    GROUP_MANAGED = ("group_managed", "集团托管")
