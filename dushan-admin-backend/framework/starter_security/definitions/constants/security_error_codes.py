from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class SecurityErrorCodes:
    """安全错误段 1_004_000～1_004_999；认证、授权与依赖故障由具体 code 区分。"""

    MISSING = ErrorCode(
        code=1_004_001,
        description="用户未登录",
        message_key="security.missing",
    )
    INVALID = ErrorCode(
        code=1_004_002,
        description="无效的访问凭据",
        message_key="security.invalid",
    )
    EXPIRED = ErrorCode(
        code=1_004_003,
        description="访问凭据已过期",
        message_key="security.expired",
    )
    REVOKED = ErrorCode(
        code=1_004_004,
        description="登录态已撤销",
        message_key="security.revoked",
    )
    DISABLED = ErrorCode(
        code=1_004_005,
        description="账号已禁用",
        message_key="security.disabled",
    )
    CREDENTIALS = ErrorCode(
        code=1_004_006,
        description="凭据已失效",
        message_key="security.credentials",
    )
    DENIED = ErrorCode(
        code=1_004_007,
        description="权限不足",
        message_key="security.denied",
    )
    ORIGIN = ErrorCode(
        code=1_004_008,
        description="请求来源不被允许",
        message_key="security.origin",
    )
    UNAVAILABLE = ErrorCode(
        code=1_004_009,
        description="安全依赖暂不可用",
        message_key="security.unavailable",
    )
    CONFIGURATION = ErrorCode(
        code=1_004_010,
        description="安全适配未配置",
        message_key="security.configuration",
    )
    CLOSED = ErrorCode(
        code=1_004_011,
        description="安全服务不可用",
        message_key="security.closed",
    )
