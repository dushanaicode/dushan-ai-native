from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO
from module_system.controller.admin.tenant.vo.packages.tenant_package_ai_quota_config_vo import (
    TenantPackageAiQuotaConfigVO,
)


class TenantPackageQuotaConfigVO(BaseRequestVO):
    """通用配额模板 VO — 承载各模块的配额模板配置"""

    ai: Annotated[TenantPackageAiQuotaConfigVO | None, Field(None, description="AI 模块配额配置")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ai": {
                        "enabled": True,
                        "billingMode": 3,
                        "monthlyTokenLimit": 500000,
                        "monthlyAmountLimit": 100.0,
                        "dailyTokenLimit": -1,
                    }
                }
            ]
        }
    }
