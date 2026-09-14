from pydantic import BaseModel, ConfigDict

from framework.starter_security.model.login_session import IdentityId
from framework.starter_security.model.workload_identity import WorkloadIdentity


class WorkloadMessage(BaseModel):
    """经证明验证的本消息授权；capability 来自签发内容，不是消费者请求值。"""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    identity: WorkloadIdentity
    capability: IdentityId

    def __repr_args__(self):
        return iter(())
