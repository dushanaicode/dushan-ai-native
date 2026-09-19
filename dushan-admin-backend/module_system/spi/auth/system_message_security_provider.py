from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_security.public import (
    MessageSecurityProvider,
)
from module_system.service.auth.system_message_service import SystemMessageService


@service(interface=MessageSecurityProvider)
class SystemMessageSecurityProvider(MessageSecurityProvider):
    delegate: SystemMessageService = Inject()

    async def issue(self, session, payload: bytes, *, audience: str):
        return await self.delegate.issue(session, payload, audience=audience)

    async def verify(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ):
        return await self.delegate.verify(
            proof, payload, application_id=application_id, domain=domain, audience=audience
        )

    async def issue_workload(self, identity, payload: bytes, *, audience: str, capability: str):
        return await self.delegate.issue_workload(
            identity, payload, audience=audience, capability=capability
        )

    async def verify_workload(
        self, proof: bytes, payload: bytes, *, application_id: str, domain: str, audience: str
    ):
        return await self.delegate.verify_workload(
            proof, payload, application_id=application_id, domain=domain, audience=audience
        )
