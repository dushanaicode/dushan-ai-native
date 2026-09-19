from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class AuthErrorCodes:
    CONFIG = ErrorCode(code=1020001, description="授权配置无效或缺失", message_key="auth.config")
    UNSUPPORTED = ErrorCode(
        code=1020002, description="授权源不支持该操作", message_key="auth.unsupported"
    )
    SOURCE = ErrorCode(code=1020003, description="授权源未注册", message_key="auth.source")
    STATE = ErrorCode(
        code=1020004, description="授权上下文无效、过期或已使用", message_key="auth.state"
    )
    INPUT = ErrorCode(code=1020005, description="授权输入无效", message_key="auth.input")
    DISABLED = ErrorCode(code=1020006, description="第三方授权未启用", message_key="auth.disabled")
    UNAVAILABLE = ErrorCode(
        code=1020007,
        description="授权资源尚未就绪或已关闭",
        message_key="auth.unavailable",
    )
    CACHE = ErrorCode(code=1020008, description="授权缓存不可用", message_key="auth.cache")
    REJECTED = ErrorCode(
        code=1020009, description="第三方拒绝授权请求", message_key="auth.rejected"
    )
    RESPONSE = ErrorCode(
        code=1020010, description="第三方授权响应无效", message_key="auth.response"
    )
    NETWORK = ErrorCode(code=1020011, description="第三方授权传输失败", message_key="auth.network")
    TIMEOUT = ErrorCode(code=1020012, description="第三方授权操作超时", message_key="auth.timeout")
    OIDC = ErrorCode(code=1020013, description="OIDC 签名或声明验证失败", message_key="auth.oidc")
    BINDING = ErrorCode(
        code=1020014, description="第三方凭据与应用配置不匹配", message_key="auth.binding"
    )
