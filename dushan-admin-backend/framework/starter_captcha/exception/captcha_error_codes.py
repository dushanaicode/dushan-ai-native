from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class CaptchaErrorCodes:
    INVALID_INPUT = ErrorCode(
        code=1_002_001, description="验证码输入无效", message_key="captcha.invalid_input"
    )
    WRONG_ANSWER = ErrorCode(
        code=1_002_002, description="验证码答案错误", message_key="captcha.wrong_answer"
    )
    EXPIRED = ErrorCode(
        code=1_002_003, description="验证码已过期或已使用", message_key="captcha.expired"
    )
    EXHAUSTED = ErrorCode(
        code=1_002_004, description="验证码尝试次数已耗尽", message_key="captcha.exhausted"
    )
    INVALID_VERIFICATION = ErrorCode(
        code=1_002_005,
        description="验证码凭证无效、过期或已使用",
        message_key="captcha.invalid_verification",
    )
    DISABLED = ErrorCode(
        code=1_002_006, description="验证码未启用", message_key="captcha.disabled", http_status=503
    )
    UNAVAILABLE = ErrorCode(
        code=1_002_007,
        description="验证码资源尚未就绪",
        message_key="captcha.unavailable",
        http_status=503,
    )
    CACHE_UNAVAILABLE = ErrorCode(
        code=1_002_011,
        description="验证码缓存不可用",
        message_key="captcha.cache_unavailable",
        http_status=503,
    )
    CORRUPT = ErrorCode(
        code=1_002_012,
        description="验证码缓存数据损坏",
        message_key="captcha.corrupt",
        http_status=503,
    )
    PROVIDER_TIMEOUT = ErrorCode(
        code=1_002_021,
        description="验证码供应商请求超时",
        message_key="captcha.provider_timeout",
        http_status=503,
    )
    PROVIDER_FAILURE = ErrorCode(
        code=1_002_022,
        description="验证码供应商服务失败",
        message_key="captcha.provider_failure",
        http_status=503,
    )
    PROVIDER_RESPONSE = ErrorCode(
        code=1_002_023,
        description="验证码供应商响应无效",
        message_key="captcha.provider_response",
        http_status=503,
    )
    CAPACITY = ErrorCode(
        code=1_002_031,
        description="验证码生成资源已达上限",
        message_key="captcha.capacity",
        http_status=429,
    )
    RESOURCE = ErrorCode(
        code=1_002_032,
        description="验证码字体资源无效",
        message_key="captcha.resource",
        http_status=503,
    )
