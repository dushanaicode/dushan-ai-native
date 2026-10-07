from pydantic import ConfigDict

from framework.common.schemas import BaseBO
from framework.starter_security.public import LoginSession
from module_system.definitions.enums.auth.qr_login_status_enum import QrLoginStatusEnum


class QrLoginStateBO(BaseBO):
    # 状态含验证码与审批会话，校验失败时不在错误中回显输入。
    model_config = ConfigDict(hide_input_in_errors=True)

    status: QrLoginStatusEnum
    tenant_id: str
    binding_digest: str
    origin: str
    code: str
    browser: str
    ip: str
    expires_at: int
    approver: LoginSession | None
