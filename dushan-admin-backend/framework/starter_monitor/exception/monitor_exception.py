from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_monitor.definitions.constants.monitor_error_codes import MonitorErrorCodes


class MonitorException(BaseBusinessException):
    """内部保留故障链，Native诊断只输出无敏感内容的投影。"""

    _system_error_codes = frozenset(
        {
            MonitorErrorCodes.INIT_FAILED.code,
            MonitorErrorCodes.INVALID_CONFIG.code,
            MonitorErrorCodes.SHUTDOWN_FAILED.code,
        }
    )

    def __safe_diagnostic__(self):
        return MonitorException(self.error_code)
