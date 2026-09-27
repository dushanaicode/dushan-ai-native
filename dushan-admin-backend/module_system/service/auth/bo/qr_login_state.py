from pydantic import BaseModel, ConfigDict

from framework.starter_security.public import LoginSession
from module_system.definitions.enums.auth.qr_login_status import QrLoginStatus


class QrLoginState(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    status: QrLoginStatus
    tenant_id: str
    binding_digest: str
    origin: str
    code: str
    browser: str
    ip: str
    expires_at: int
    approver: LoginSession | None
