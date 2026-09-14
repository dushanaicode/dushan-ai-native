from dataclasses import dataclass, field
from datetime import datetime

from framework.common.security.request_identity import RequestIdentity
from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.model.request_audit import RequestAudit


@dataclass(frozen=True, slots=True)
class LogRecordOperation:
    """业务开始前冻结的最小安全投影，不含请求体、凭据或完整主体。"""

    event_id: str
    type: str
    sub_type: str
    occurred_at: datetime
    identity: RequestIdentity = field(repr=False)
    realm: SecurityRealm
    actor_tenant_id: str | None = field(repr=False)
    membership_id: str | None = field(repr=False)
    trace_id: str | None
    request: RequestAudit | None = field(default=None, repr=False)
