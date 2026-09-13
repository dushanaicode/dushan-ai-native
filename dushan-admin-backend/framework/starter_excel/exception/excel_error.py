from collections.abc import Sequence

from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.field_error import FieldError
from framework.common.exception.exceptions.server_exception import ServerException
from framework.starter_excel.exception.excel_error_codes import ExcelErrorCodes
from framework.starter_excel.model.excel_issue import ExcelIssue


class ExcelError(ServerException):
    """保留底层异常链与有界行列诊断；公开信息不包含上传单元格原值。"""

    default_error_code = ExcelErrorCodes.ERROR

    def __init__(
        self,
        error_code: ErrorCode,
        msg: str,
        *,
        issues: Sequence[ExcelIssue] = (),
        cause: Exception | None = None,
    ) -> None:
        self.issues = tuple(issues)
        super().__init__(
            error_code=error_code,
            msg=msg,
            cause=cause,
            field_errors=[
                FieldError(
                    field=f"R{issue.row}C{issue.column or ''}.{issue.field}",
                    message=issue.message,
                )
                for issue in self.issues
            ],
        )
