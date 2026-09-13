from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants
from framework.starter_ip.exception.ip_exception import IpException


class IpProviderError(IpException):
    """可按显式策略继续下一在线 Provider 的网络、解码或协议故障。"""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(
            IpErrorCodeConstants.QUERY_FAILED, context={"provider": provider, "reason": reason}
        )
