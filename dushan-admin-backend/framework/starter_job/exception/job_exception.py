from framework.common.exception.exceptions.base_business_exception import BaseBusinessException
from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes


class JobException(BaseBusinessException):
    """任务调度的唯一异常；失败原因由 JobErrorCodes 区分，诊断只保留错误码。"""

    _system_error_codes = frozenset(
        {
            JobErrorCodes.ERROR.code,
            JobErrorCodes.CONFIGURATION.code,
            JobErrorCodes.OWNER.code,
            JobErrorCodes.CLOSED.code,
        }
    )

    default_error_code = JobErrorCodes.ERROR

    def __safe_diagnostic__(self) -> "JobException":
        return JobException(self.error_code)
