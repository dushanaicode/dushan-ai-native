from typing import Protocol, runtime_checkable

from framework.starter_database.public import DataSourceSettings


@runtime_checkable
class DataSourceRuntimeService(Protocol):
    """把已启用的数据源配置提供给数据库运行时作为具名数据源。"""

    async def load_sources(self) -> tuple[DataSourceSettings, ...]: ...
