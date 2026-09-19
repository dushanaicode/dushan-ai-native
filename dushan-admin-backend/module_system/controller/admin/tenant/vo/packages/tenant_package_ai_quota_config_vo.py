from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class TenantPackageAiQuotaConfigVO(BaseRequestVO):
    """AI 模块配额模板配置（嵌套在 quota_config.ai 中）"""

    enabled: Annotated[bool, Field(True, description="是否启用 AI 模块")]
    billing_mode: Annotated[
        int, Field(1, description="计费模式【BillingModeEnum】1=纯配额 2=纯余额 3=混合")
    ]
    monthly_token_limit: Annotated[int, Field(-1, description="月 Token 总额度（-1=无限）")]
    monthly_amount_limit: Annotated[float, Field(-1, description="月金额总额度（元，-1=无限）")]
    daily_token_limit: Annotated[int, Field(-1, description="日 Token 限额（-1=无限）")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "enabled": True,
                    "billingMode": 3,
                    "monthlyTokenLimit": 500000,
                    "monthlyAmountLimit": 100.0,
                    "dailyTokenLimit": -1,
                }
            ]
        }
    }
