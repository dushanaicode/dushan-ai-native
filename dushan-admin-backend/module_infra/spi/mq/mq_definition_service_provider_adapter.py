from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    ConsumerOverrideProvider,
)
from module_infra.service.mq.mq_definition_store import MqDefinitionStore


@service(interface=ConsumerOverrideProvider)
class MqDefinitionServiceProviderAdapter(ConsumerOverrideProvider):
    store: MqDefinitionStore = Inject()

    async def load(self):
        return await self.store.load_overrides()
