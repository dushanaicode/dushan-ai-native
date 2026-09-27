from framework.starter_di.decorators.components import framework
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_security.config.security_settings import SecuritySettings
from framework.starter_security.core.security_service import SecurityService
from framework.starter_security.spi.security_execution_provider import SecurityExecutionProvider


@framework(interface=SecurityExecutionProvider, scope=ComponentScopeEnum.SINGLETON)
@conditional(lambda config: config.get_config(SecuritySettings).enabled)
class SecurityExecutionProviderAdapter(SecurityExecutionProvider):
    """只转交可信执行，不复制鉴权算法、重建身份或增加异步执行边界。"""

    def __init__(self, service: SecurityService):
        self.service = service

    @property
    def application_id(self) -> str:
        return self.service.settings.application_id

    @property
    def context(self):
        return self.service.context

    def validate_policy(self, policy):
        self.service.validate_policy(policy)

    async def run_workload(
        self, source, callback, *args, capability, tenant_id=None, domain=None, **kwargs
    ):
        return await self.service.run_workload(
            source,
            callback,
            *args,
            capability=capability,
            tenant_id=tenant_id,
            domain=domain,
            **kwargs,
        )

    async def issue_message(self, payload, *, audience):
        return await self.service.issue_message(payload, audience=audience)

    async def run_message(self, proof, payload, policy, callback, *args, audience, **kwargs):
        return await self.service.run_message(
            proof, payload, policy, callback, *args, audience=audience, **kwargs
        )

    async def issue_workload_message(self, payload, *, audience, capability):
        return await self.service.issue_workload_message(
            payload, audience=audience, capability=capability
        )

    async def run_workload_message(
        self, proof, payload, callback, *args, audience, capability, domain=None, **kwargs
    ):
        return await self.service.run_workload_message(
            proof,
            payload,
            callback,
            *args,
            audience=audience,
            capability=capability,
            domain=domain,
            **kwargs,
        )

    async def run_authenticated(self, resolver, policy, callback, *args, **kwargs):
        return await self.service.run_authenticated(resolver, policy, callback, *args, **kwargs)

    async def run_session_reference(self, expected, policy, callback, *args, **kwargs):
        return await self.service.run_session_reference(expected, policy, callback, *args, **kwargs)

    async def allowed_policies(self, policies):
        return await self.service.allowed_policies(policies)
