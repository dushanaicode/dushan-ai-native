from framework.starter_database.public import (
    DataSourceConfigProvider,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from module_infra.service.data_source.data_source_config_store import DataSourceConfigStore


@service(interface=DataSourceConfigProvider)
class DataSourceConfigProviderAdapter(DataSourceConfigProvider):
    store: DataSourceConfigStore = Inject()

    async def load_sources(self):
        return await self.store.load_sources()
