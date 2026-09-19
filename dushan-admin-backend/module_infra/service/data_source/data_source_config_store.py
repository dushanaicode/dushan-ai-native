from sqlalchemy import select

from framework.starter_database.public import (
    DatabasePoolSettings,
    DatabaseSettings,
    DataSourceSettings,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO
from module_infra.dal.mapper.data_source.data_source_config_mapper import DataSourceConfigMapper


@service
class DataSourceConfigStore:
    mapper: DataSourceConfigMapper = Inject()
    settings: DatabaseSettings = Inject()

    def source(self, row):
        return DataSourceSettings(
            name=f"infra_{row.id}",
            url=row.url,
            role="named",
            weight=100,
            tls=None,
            pool=DatabasePoolSettings(
                size=row.pool_size,
                max_overflow=row.max_overflow,
                timeout_seconds=float(row.pool_timeout),
                recycle_seconds=row.pool_recycle,
                pre_ping=True,
            ),
        )

    async def load_sources(self):
        rows = (
            (
                await self.mapper.read_from_primary(
                    select(DataSourceConfigDO).where(DataSourceConfigDO.status == 1)
                )
            )
            .scalars()
            .all()
        )
        return tuple(self.source(row) for row in rows)
