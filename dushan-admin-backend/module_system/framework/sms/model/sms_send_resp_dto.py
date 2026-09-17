from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class SmsSendRespDTO(BaseDTO):
    """短信发送 Response DTO"""

    success: bool = Field(..., description="Provider 是否明确接受发送请求")
    api_request_id: str | None = Field(default=None, description="API请求ID")
    serial_no: str | None = Field(default=None, description="序列号")
    api_code: str | None = Field(default=None, description="API代码")
    api_msg: str | None = Field(default=None, description="API消息")
