from pydantic import Field, model_validator

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
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
        allowed = {
            "account_selection",
            "group_managed_access",
            "group_data_sharing",
            "platform_control_plane",
            "manual_provisioning",
            "self_service_provisioning",
            "support_session",
        }
        if not self.custom_capabilities <= allowed:
            raise ValueError("租户部署能力不在支持范围内")
        dependencies = {
            "group_data_sharing": "group_managed_access",
            "group_managed_access": "account_selection",
            "manual_provisioning": "platform_control_plane",
            "self_service_provisioning": "platform_control_plane",
            "support_session": "platform_control_plane",
        }
        if any(
            cap in self.custom_capabilities and required not in self.custom_capabilities
            for cap, required in dependencies.items()
        ):
            raise ValueError("租户部署能力缺少依赖")
        return self

    def capabilities(self) -> frozenset[str]:
        if not self.enabled:
            return frozenset({"direct_membership"})
        profiles = {
            TenantDeploymentProfile.SINGLE_ORGANIZATION: frozenset(),
            TenantDeploymentProfile.INTERNAL_GROUP: frozenset(
                {"account_selection", "group_managed_access", "group_data_sharing"}
            ),
            TenantDeploymentProfile.EXTERNAL_HOSTED: frozenset(
                {
                    "account_selection",
                    "platform_control_plane",
                    "manual_provisioning",
                    "self_service_provisioning",
                    "support_session",
                }
            ),
            TenantDeploymentProfile.CUSTOM: self.custom_capabilities,
        }
        return profiles[self.profile] | {"direct_membership"}
