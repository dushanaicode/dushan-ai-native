from pydantic import Field, model_validator

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorators.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
from framework.starter_tenant.definitions.constants.tenant_capabilities import TenantCapabilities
from framework.starter_tenant.definitions.enums.tenant_deployment_profile import (
    TenantDeploymentProfile,
)


@config_model(
    "tenant", env_prefix="TENANT_", sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML)
)
class TenantSettings(ConfigModel):
    enabled: bool
    default_tenant_id: str = Field(strict=True, min_length=1, max_length=256)
    profile: TenantDeploymentProfile
    custom_capabilities: frozenset[str]
    provider_timeout_seconds: float = Field(gt=0, le=60, allow_inf_nan=False)
    execution_seconds: float = Field(gt=0, le=86400, allow_inf_nan=False)
    target_batch_size: int = Field(strict=True, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_profile(self):
        if self.profile is not TenantDeploymentProfile.CUSTOM and self.custom_capabilities:
            raise ValueError("只有自定义部署方案可以声明能力集合")
        if not self.custom_capabilities <= TenantCapabilities.CUSTOM:
            raise ValueError("租户部署能力不在支持范围内")
        dependencies = {
            TenantCapabilities.GROUP_DATA_SHARING: TenantCapabilities.GROUP_MANAGED_ACCESS,
            TenantCapabilities.GROUP_MANAGED_ACCESS: TenantCapabilities.ACCOUNT_SELECTION,
            TenantCapabilities.MANUAL_PROVISIONING: TenantCapabilities.PLATFORM_CONTROL_PLANE,
            TenantCapabilities.SELF_SERVICE_PROVISIONING: TenantCapabilities.PLATFORM_CONTROL_PLANE,
            TenantCapabilities.SUPPORT_SESSION: TenantCapabilities.PLATFORM_CONTROL_PLANE,
        }
        if any(
            cap in self.custom_capabilities and required not in self.custom_capabilities
            for cap, required in dependencies.items()
        ):
            raise ValueError("租户部署能力缺少依赖")
        return self

    def capabilities(self) -> frozenset[str]:
        if not self.enabled:
            return frozenset({TenantCapabilities.DIRECT_MEMBERSHIP})
        profiles = {
            TenantDeploymentProfile.SINGLE_ORGANIZATION: frozenset(),
            TenantDeploymentProfile.INTERNAL_GROUP: frozenset(
                {
                    TenantCapabilities.ACCOUNT_SELECTION,
                    TenantCapabilities.GROUP_MANAGED_ACCESS,
                    TenantCapabilities.GROUP_DATA_SHARING,
                }
            ),
            TenantDeploymentProfile.EXTERNAL_HOSTED: frozenset(
                {
                    TenantCapabilities.ACCOUNT_SELECTION,
                    TenantCapabilities.PLATFORM_CONTROL_PLANE,
                    TenantCapabilities.MANUAL_PROVISIONING,
                    TenantCapabilities.SELF_SERVICE_PROVISIONING,
                    TenantCapabilities.SUPPORT_SESSION,
                }
            ),
            TenantDeploymentProfile.CUSTOM: self.custom_capabilities,
        }
        return profiles[self.profile] | {TenantCapabilities.DIRECT_MEMBERSHIP}
