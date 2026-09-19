from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)


class WebSocketException(BaseBusinessException):
    """WebSocket 的唯一异常；只发布安全原因，不携带原始帧、票据或完整主体。"""

    _system_error_codes = frozenset(
        {
            WebSocketErrorCodes.CONFIGURATION.code,
            WebSocketErrorCodes.CLOSED.code,
            WebSocketErrorCodes.CAPACITY.code,
            WebSocketErrorCodes.TRANSPORT.code,
        }
    )

    default_error_code = WebSocketErrorCodes.ERROR

    def __safe_diagnostic__(self) -> "WebSocketException":
        return WebSocketException(self.error_code)
