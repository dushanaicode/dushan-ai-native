from framework.common.schemas import BaseVO
from module_system.definitions.enums.auth.qr_login_status_enum import QrLoginStatusEnum


class AuthQrStatusRespVO(BaseVO):
    status: QrLoginStatusEnum
