from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.inject import Inject
from framework.starter_mq.spi.consumer_override_provider import ConsumerOverrideProvider
from module_infra.service.mq.mq_definition_store import MqDefinitionStore


@service(interface=ConsumerOverrideProvider)
class MqDefinitionServiceProviderAdapter(ConsumerOverrideProvider):
    store: MqDefinitionStore = Inject()

    async def load(self):
        return await self.store.load_overrides()
