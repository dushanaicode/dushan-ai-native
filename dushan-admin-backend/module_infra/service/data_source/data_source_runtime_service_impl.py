from typing import override

from sqlalchemy import select

from framework.starter_database.public import (
    DatabasePoolSettings,
    DataSourceSettings,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO
from module_infra.dal.mapper.data_source.data_source_config_mapper import DataSourceConfigMapper
from module_infra.service.data_source.data_source_runtime_service import (
    DataSourceRuntimeService,
)


@service(interface=DataSourceRuntimeService)
class DataSourceRuntimeServiceImpl(DataSourceRuntimeService):
    """读取已启用的数据源配置并转换为具名运行时数据源。"""

    mapper: DataSourceConfigMapper = Inject()

    @staticmethod
    def _source(row):
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

    @override
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
        return tuple(self._source(row) for row in rows)
