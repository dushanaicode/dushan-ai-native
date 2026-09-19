from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.registry.error_code_decorator import error_code


@error_code
class GlobalErrorCodeConstants:
    """提供公共错误分类，导入后可交给 ErrorCodeRegistry 注册。

    约束：
    - 0：成功
    - 1~999：系统保留段（含 HTTP 类错误码映射）
    - 1000 起：业务错误，由所属模块分配并通过注册器校验冲突

    例如 raise BaseBusinessException(GlobalErrorCodeConstants.BAD_REQUEST)。
    所有编号均为应用错误码；普通业务响应固定 HTTP 200，不从编号推导 HTTP 状态。
    """

    SUCCESS = ErrorCode(
        code=0,
        description="成功",
        message_key="exception.success",
    )

    # ========== 客户端错误段 ==========
    BAD_REQUEST = ErrorCode(
        code=400,
        description="请求参数不正确",
        message_key="exception.bad_request",
    )
    UNAUTHORIZED = ErrorCode(
        code=401,
        description="账号未登录",
        message_key="exception.unauthorized",
    )
    FORBIDDEN = ErrorCode(
        code=403,
        description="没有该操作权限",
        message_key="exception.forbidden",
    )
    NOT_FOUND = ErrorCode(
        code=404,
        description="请求未找到",
        message_key="exception.not_found",
    )
    METHOD_NOT_ALLOWED = ErrorCode(
        code=405,
        description="请求方法不正确",
        message_key="exception.method_not_allowed",
    )
    CONFLICT = ErrorCode(
        code=409,
        description="请求冲突/资源状态冲突",
        message_key="exception.conflict",
    )
    PAYLOAD_TOO_LARGE = ErrorCode(
        code=413,
        description="请求体过大",
        message_key="exception.payload_too_large",
    )
    LOCKED = ErrorCode(
        code=423,
        description="请求失败，请稍后重试",
        message_key="exception.locked",
    )
    TOO_MANY_REQUESTS = ErrorCode(
        code=429,
        description="请求过于频繁，请稍后重试",
        message_key="exception.too_many_requests",
    )
    VALIDATION_ERROR = ErrorCode(
        code=422,
        description="请求参数不正确",
        message_key="exception.validation_error",
    )

    # ========== 服务端错误段 ==========
    INTERNAL_SERVER_ERROR = ErrorCode(
        code=500,
        description="系统异常",
        message_key="exception.internal_server_error",
    )
    NOT_IMPLEMENTED = ErrorCode(
        code=501,
        description="功能未实现/未开启",
        message_key="exception.not_implemented",
    )
    ERROR_CONFIGURATION = ErrorCode(
        code=502,
        description="错误的配置项",
        message_key="exception.error_configuration",
    )
    # 业务码 502 已用于配置错误，网关故障使用独立公共编号。
    BAD_GATEWAY = ErrorCode(
        code=903,
        description="上游服务响应异常",
        message_key="exception.bad_gateway",
    )
    SERVICE_UNAVAILABLE = ErrorCode(
        code=503,
        description="服务暂时不可用",
        message_key="exception.service_unavailable",
    )

    # ========== 自定义错误段 ==========
    REPEATED_REQUESTS = ErrorCode(
        code=900,
        description="重复请求，请稍后重试",
        message_key="exception.repeated_requests",
    )
    DEMO_DENY = ErrorCode(
        code=901,
        description="演示模式，禁止写操作",
        message_key="exception.demo_deny",
    )
    SIGNATURE_MISMATCH = ErrorCode(
        code=902,
        description="签名不匹配",
        message_key="exception.signature_mismatch",
    )
