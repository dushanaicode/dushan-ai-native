from typing import override

from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_mq.public import (
    ConsumerOverride,
    ConsumerOverrideProvider,
)
from module_infra.service.mq.mq_consumer_override_service import MqConsumerOverrideService


@service(interface=ConsumerOverrideProvider)
class MqDefinitionServiceProviderAdapter(ConsumerOverrideProvider):
    store: MqConsumerOverrideService = Inject()

    @override
    async def load(self) -> dict[str, ConsumerOverride]:
        return await self.store.load_overrides()
