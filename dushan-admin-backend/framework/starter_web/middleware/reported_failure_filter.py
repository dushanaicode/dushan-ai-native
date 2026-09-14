import logging

from framework.starter_web.exception.reported_http_failure import ReportedHttpFailure


class ReportedFailureFilter(logging.Filter):
    """只去除本应用已经记录的宿主重复故障，不过滤其他异常。"""

    def __init__(self, owner: str) -> None:
        super().__init__()
        self.owner = owner

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info is not None:
            error = record.exc_info[1]
            return not isinstance(error, ReportedHttpFailure) or error.owner != self.owner
        # Granian 2.7.6 把异常格式化后交给 _granian，而不是传递 exc_info。
        message = record.getMessage()
        return not (
            (record.name == "_granian" or record.name.startswith("_granian."))
            and message.startswith("Application callable raised an exception\n")
            and message.endswith(str(ReportedHttpFailure(self.owner)))
        )
