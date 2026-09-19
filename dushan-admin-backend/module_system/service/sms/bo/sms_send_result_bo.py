from framework.common.schemas import BaseBO


class SmsSendResultBO(BaseBO):
    id: int
    success: bool
    api_send_code: str | None
    api_send_msg: str | None
    api_request_id: str | None
    api_serial_no: str | None
