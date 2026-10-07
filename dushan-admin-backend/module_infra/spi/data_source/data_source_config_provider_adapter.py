from typing import override

from framework.starter_database.public import (
    DataSourceConfigProvider,
    DataSourceSettings,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.service.data_source.data_source_runtime_service import (
    DataSourceRuntimeService,
)


@service(interface=DataSourceConfigProvider)
class DataSourceConfigProviderAdapter(DataSourceConfigProvider):
    store: DataSourceRuntimeService = Inject()

    @override
    async def load_sources(self) -> tuple[DataSourceSettings, ...]:
        return await self.store.load_sources()
