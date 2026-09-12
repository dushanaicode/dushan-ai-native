import asyncio
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncEngine

from framework.starter_database.config.data_source_settings import DataSourceSettings


@dataclass(eq=False, slots=True)
class EngineEntry:
    """一个引擎的配置、实际租用计数与退休信号。"""

    source: DataSourceSettings
    engine: AsyncEngine
    leases: int = 0
    healthy: bool = True
    retired: bool = False
    drained: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self.drained.set()

    def acquire(self) -> None:
        if self.retired:
            raise RuntimeError("不能租用已退休的数据源")
        self.leases += 1
        self.drained.clear()

    def release(self) -> None:
        if self.leases <= 0:
            raise RuntimeError("数据源租约重复释放")
        self.leases -= 1
        if self.leases == 0:
            self.drained.set()
