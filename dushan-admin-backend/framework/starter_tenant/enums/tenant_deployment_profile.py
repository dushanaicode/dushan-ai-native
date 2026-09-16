from framework.common.enums.base_enum import BaseEnum


class TenantDeploymentProfile(BaseEnum):
    """部署期声明的租户能力集合来源。"""

    SINGLE_ORGANIZATION = ("single_organization", "单组织")
    INTERNAL_GROUP = ("internal_group", "内部集团")
    EXTERNAL_HOSTED = ("external_hosted", "对外托管")
    CUSTOM = ("custom", "自定义")
