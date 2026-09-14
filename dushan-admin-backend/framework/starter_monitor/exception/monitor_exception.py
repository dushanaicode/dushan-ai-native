from framework.common.exception.exceptions.base_business_exception import BaseBusinessException


class MonitorException(BaseBusinessException):
    """内部保留故障链，Native诊断只输出无敏感内容的投影。"""

    def __safe_diagnostic__(self):
        return MonitorException(self.error_code, http_status=self.http_status)
