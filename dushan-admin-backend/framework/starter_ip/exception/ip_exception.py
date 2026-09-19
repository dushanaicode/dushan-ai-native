from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes


class IpException(ServerException):
    """IP 组件的唯一异常；失败原因由 IpErrorCodes 区分。

    地址族未启用与在线 Provider 故障分别把 family、provider、reason 放入 context，
    供 Provider 链判断是跳过本地库还是按策略继续下一个在线源。
    """

    default_error_code = IpErrorCodes.IP_ERROR
    retryable = False
