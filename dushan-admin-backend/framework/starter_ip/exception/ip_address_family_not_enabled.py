from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants
from framework.starter_ip.exception.ip_exception import IpException


class IpAddressFamilyNotEnabled(IpException):
    """所查询地址族未加载；它是模式选择，不代表 XDB 损坏或正常未命中。"""

    def __init__(self, family: int) -> None:
        self.family = family
        super().__init__(IpErrorCodeConstants.FAMILY_NOT_ENABLED, context={"family": family})
