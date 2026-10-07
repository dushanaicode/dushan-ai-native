from typing import Protocol

from framework.starter_config.provider.config_update_result import ConfigUpdateResult


class ConfigSourceProvider(Protocol):
    """由业务模块提供外部配置刷新能力。"""

    async def refresh(self) -> ConfigUpdateResult: ...
