from pydantic import StrictBool

from module_system.controller.admin.auth.vo.auth_qr_ticket_req_vo import AuthQrTicketReqVO


class AuthQrConfirmReqVO(AuthQrTicketReqVO):
    approve: StrictBool
