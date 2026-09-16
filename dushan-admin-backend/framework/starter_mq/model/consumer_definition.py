from pydantic import BaseModel, ConfigDict
from pydantic.dataclasses import dataclass

from framework.starter_mq.enums.exhausted_policy import ExhaustedPolicy
from framework.starter_mq.enums.message_mode import MessageMode
from framework.starter_mq.enums.tenant_policy import TenantPolicy
from framework.starter_mq.model.retry_policy import RetryPolicy
from framework.starter_web.routing.route_policy import RoutePolicy


@dataclass(
    frozen=True,
    slots=True,
    config=ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True),
)
class ConsumerDefinition:
    """稳定 key、消息模型及身份/租户语义由代码一次声明。"""

    key: str
    destination: str
    mode: MessageMode
    message: type[BaseModel]
    group: str | None
    retry: RetryPolicy
    exhausted: ExhaustedPolicy
    tenant_policy: TenantPolicy
    session_policy: RoutePolicy | None
    workload_capabilities: frozenset[str]
    external_authenticator: type | None = None
