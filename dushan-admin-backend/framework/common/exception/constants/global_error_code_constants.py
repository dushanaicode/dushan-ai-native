from http import HTTPStatus

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
    编号和 HTTP 状态分别读取，不能将自定义业务编号直接作为 HTTP 状态。
    """

    SUCCESS = ErrorCode(
        code=0,
        description="成功",
        message_key="exception.success",
        http_status=HTTPStatus.OK,
    )

    # ========== 客户端错误段 ==========
    BAD_REQUEST = ErrorCode(
        code=400,
        description="请求参数不正确",
        message_key="exception.bad_request",
        http_status=HTTPStatus.BAD_REQUEST,
    )
    UNAUTHORIZED = ErrorCode(
        code=401,
        description="账号未登录",
        message_key="exception.unauthorized",
        http_status=HTTPStatus.UNAUTHORIZED,
    )
    FORBIDDEN = ErrorCode(
        code=403,
        description="没有该操作权限",
        message_key="exception.forbidden",
        http_status=HTTPStatus.FORBIDDEN,
    )
    NOT_FOUND = ErrorCode(
        code=404,
        description="请求未找到",
        message_key="exception.not_found",
        http_status=HTTPStatus.NOT_FOUND,
    )
    METHOD_NOT_ALLOWED = ErrorCode(
        code=405,
        description="请求方法不正确",
        message_key="exception.method_not_allowed",
        http_status=HTTPStatus.METHOD_NOT_ALLOWED,
    )
    CONFLICT = ErrorCode(
        code=409,
        description="请求冲突/资源状态冲突",
        message_key="exception.conflict",
        http_status=HTTPStatus.CONFLICT,
    )
    PAYLOAD_TOO_LARGE = ErrorCode(
        code=413,
        description="请求体过大",
        message_key="exception.payload_too_large",
        http_status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    )
    LOCKED = ErrorCode(
        code=423,
        description="请求失败，请稍后重试",
        message_key="exception.locked",
        http_status=HTTPStatus.LOCKED,
    )
    TOO_MANY_REQUESTS = ErrorCode(
        code=429,
        description="请求过于频繁，请稍后重试",
        message_key="exception.too_many_requests",
        http_status=HTTPStatus.TOO_MANY_REQUESTS,
    )
    VALIDATION_ERROR = ErrorCode(
        code=422,
        description="请求参数不正确",
        message_key="exception.validation_error",
        http_status=HTTPStatus.UNPROCESSABLE_ENTITY,
    )

    # ========== 服务端错误段 ==========
    INTERNAL_SERVER_ERROR = ErrorCode(
        code=500,
        description="系统异常",
        message_key="exception.internal_server_error",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    NOT_IMPLEMENTED = ErrorCode(
        code=501,
        description="功能未实现/未开启",
        message_key="exception.not_implemented",
        http_status=HTTPStatus.NOT_IMPLEMENTED,
    )
    ERROR_CONFIGURATION = ErrorCode(
        code=502,
        description="错误的配置项",
        message_key="exception.error_configuration",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    # 业务码 502 已用于配置错误，网关故障使用独立公共编号。
    BAD_GATEWAY = ErrorCode(
        code=903,
        description="上游服务响应异常",
        message_key="exception.bad_gateway",
        http_status=HTTPStatus.BAD_GATEWAY,
    )
    SERVICE_UNAVAILABLE = ErrorCode(
        code=503,
        description="服务暂时不可用",
        message_key="exception.service_unavailable",
        http_status=HTTPStatus.SERVICE_UNAVAILABLE,
    )

    # ========== 自定义错误段 ==========
    REPEATED_REQUESTS = ErrorCode(
        code=900,
        description="重复请求，请稍后重试",
        message_key="exception.repeated_requests",
        http_status=HTTPStatus.CONFLICT,
    )
    DEMO_DENY = ErrorCode(
        code=901,
        description="演示模式，禁止写操作",
        message_key="exception.demo_deny",
        http_status=HTTPStatus.FORBIDDEN,
    )
    SIGNATURE_MISMATCH = ErrorCode(
        code=902,
        description="签名不匹配",
        message_key="exception.signature_mismatch",
        http_status=HTTPStatus.UNAUTHORIZED,
    )
