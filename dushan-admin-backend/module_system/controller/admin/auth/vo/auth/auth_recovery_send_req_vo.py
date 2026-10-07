from pydantic import Field

from module_system.controller.admin.auth.vo.auth.auth_recovery_contact_req_vo import (
    AuthRecoveryContactReqVO,
)


class AuthRecoverySendReqVO(AuthRecoveryContactReqVO):
    verification: str | None = Field(None, min_length=1)
