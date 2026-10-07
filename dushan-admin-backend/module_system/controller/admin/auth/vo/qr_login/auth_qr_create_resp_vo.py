from framework.common.contracts import SnowflakeIdStr
from framework.common.schemas import BaseVO


class AuthQrCreateRespVO(BaseVO):
    ticket: str
    code: str
    tenant_id: SnowflakeIdStr
    expires_at: int
    poll_interval: int
