from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants


class IpException(ServerException):
    default_error_code = IpErrorCodeConstants.IP_ERROR
    retryable = False
