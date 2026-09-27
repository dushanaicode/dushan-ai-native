from framework.common.schemas import BaseVO
from module_system.definitions.enums.auth.qr_login_status import QrLoginStatus


class AuthQrStatusRespVO(BaseVO):
    status: QrLoginStatus
