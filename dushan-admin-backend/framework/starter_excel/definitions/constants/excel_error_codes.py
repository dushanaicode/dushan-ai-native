from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class ExcelErrorCodes:
    """Excel 文件、契约、转换和资源边界的错误分类。"""

    ERROR = ErrorCode(code=1_014_000, description="Excel 操作失败", message_key="excel.error")
    READ = ErrorCode(code=1_014_001, description="读取 XLSX 失败", message_key="excel.read_failed")
    WRITE = ErrorCode(
        code=1_014_011, description="写入 XLSX 失败", message_key="excel.write_failed"
    )
    VALIDATION = ErrorCode(
        code=1_014_022, description="Excel 数据校验失败", message_key="excel.validation_failed"
    )
    CONFIG = ErrorCode(
        code=1_014_023, description="Excel 列定义无效", message_key="excel.config_failed"
    )
    LIMIT = ErrorCode(
        code=1_014_028, description="Excel 资源超过限制", message_key="excel.limit_exceeded"
    )
    CONVERSION = ErrorCode(
        code=1_014_031, description="Excel 字段转换失败", message_key="excel.conversion_failed"
    )
