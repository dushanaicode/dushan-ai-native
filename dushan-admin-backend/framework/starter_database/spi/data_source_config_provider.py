from typing import Protocol

from framework.starter_database.config.data_source_settings import DataSourceSettings


class DataSourceConfigProvider(Protocol):
    """由 Infra 等上层提供已启用的完整 named 快照，数据库不导入业务模型。"""

    async def load_sources(self) -> tuple[DataSourceSettings, ...]: ...
