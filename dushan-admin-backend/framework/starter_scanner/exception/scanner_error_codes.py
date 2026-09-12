from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class ScannerErrorCodes:
    """扫描器静态错误定义；保留明确在用的编号，不承诺冻结或硬超时接口。"""

    SCANNER_ERROR = ErrorCode(code=1_018_000, description="扫描器异常", message_key="scanner.error")
    SCANNER_CONFIG_ERROR = ErrorCode(
        code=1_018_001, description="扫描器配置错误", message_key="scanner.config_error"
    )
    SCANNER_MISSING_METADATA = ErrorCode(
        code=1_018_003, description="组件元数据非法", message_key="scanner.missing_metadata"
    )
    SCANNER_MODULE_IMPORT_ERROR = ErrorCode(
        code=1_018_011, description="模块导入失败", message_key="scanner.module_import_error"
    )
    SCANNER_SECURITY_ERROR = ErrorCode(
        code=1_018_012, description="扫描来源不符合声明", message_key="scanner.security_error"
    )
