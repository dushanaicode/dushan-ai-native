from datetime import datetime

from pydantic import Field

from framework.common.schemas import BaseDTO


class SmsReceiveRespDTO(BaseDTO):
    """消息接收 Response DTO"""

    success: bool | None = Field(default=None)
    error_code: str | None = Field(default=None)
    error_msg: str | None = Field(default=None)
    mobile: str | None = Field(default=None)
    receive_time: datetime | None = Field(default=None)
    serial_no: str | None = Field(default=None)
    log_id: int | None = Field(default=None)
