from datetime import datetime

from framework.common.schemas import BaseBO


class SmsReceiveResultBO(BaseBO):
    id: int
    success: bool
    receive_time: datetime
    api_receive_code: str | None
    api_receive_msg: str | None
