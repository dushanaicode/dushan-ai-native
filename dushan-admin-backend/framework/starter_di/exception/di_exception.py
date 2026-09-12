from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_di.exception.di_error_codes import DiErrorCodes


class DiException(ServerException):
    """保留声明、注入及生命周期故障的原始原因。"""

    default_error_code = DiErrorCodes.ERROR
    log_level = LogLevelEnum.ERROR
