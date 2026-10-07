from framework.common.contracts import SnowflakeIdStr
from framework.common.schemas import BaseVO
from module_system.definitions.enums.auth.qr_login_status_enum import QrLoginStatusEnum


class AuthQrScanRespVO(BaseVO):
    status: QrLoginStatusEnum
    tenant_id: SnowflakeIdStr
    code: str
    browser: str
    ip: str
    expires_at: int
