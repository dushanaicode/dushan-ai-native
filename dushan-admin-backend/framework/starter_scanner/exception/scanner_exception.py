from framework.common.enums.log_level_enum import LogLevelEnum
from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_scanner.exception.scanner_error_codes import ScannerErrorCodes


class ScannerException(ServerException):
    """扫描失败保留完整业务异常参数与原始原因，不依赖翻译器已启动。"""

    default_error_code = ScannerErrorCodes.SCANNER_ERROR
    log_level = LogLevelEnum.ERROR
