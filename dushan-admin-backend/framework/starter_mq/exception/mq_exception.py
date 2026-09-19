from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes


class MQException(BaseBusinessException):
    """消息队列的唯一异常；诊断仅保留错误码，凭证和原始消息不会进入响应。"""

    _system_error_codes = frozenset(
        {
            MQErrorCodes.ERROR.code,
            MQErrorCodes.CONFIGURATION.code,
            MQErrorCodes.CLOSED.code,
            MQErrorCodes.CAPACITY.code,
            MQErrorCodes.UNKNOWN.code,
            MQErrorCodes.CONFIRMATION.code,
            MQErrorCodes.LEASE.code,
        }
    )

    default_error_code = MQErrorCodes.ERROR

    def __safe_diagnostic__(self) -> "MQException":
        return MQException(self.error_code)
