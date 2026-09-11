from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from loguru import logger
from starlette.exceptions import HTTPException

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.exception_trace_reporter import ExceptionTraceReporter
from framework.common.exception.core.exception_translator import ExceptionTranslator
from framework.common.exception.exceptions.base_business_exception import (
    BaseBusinessException,
)
from framework.common.exception.utils.error_log_recorder import ErrorLogRecorder
from framework.common.exception.utils.exception_logger import ExceptionLogger
from framework.common.exception.utils.exception_util import ExceptionUtil
from framework.common.exception.utils.response_builder import ExceptionResponseBuilder
from framework.common.exception.utils.validation_error_mapper import ValidationErrorMapper
from framework.common.response.core.response_headers import ResponseHeaders
from framework.common.security.sanitizer import Sanitizer


class GlobalExceptionHandler:
    """全局异常处理器。

    统一封装对 Starlette/FastAPI HTTPException、请求校验异常、业务异常以及系统未捕获异常的响应与记录逻辑。
    每个应用创建自己的实例，将记录器、翻译器、调试开关与追踪器在构造时传入。
    调用 register(app) 完成注册；缺省不记录到外部服务，也不输出调试详情。
    """

    def __init__(
        self,
        trace_reporter: ExceptionTraceReporter | None = None,
        *,
        translator: ExceptionTranslator | None = None,
        error_recorder: ErrorLogRecorder | None = None,
        debug: bool = False,
    ) -> None:
        """保存当前应用的异常处理依赖，不读写其他应用的配置。"""
        self.trace_reporter = trace_reporter
        self.translator = translator
        self.error_recorder = error_recorder
        self.debug = debug

    def register(self, app: FastAPI) -> None:
        """将当前处理器实例的各异常处理方法注册至 FastAPI 应用。"""
        app.add_exception_handler(HTTPException, self.handle_http_exception)
        app.add_exception_handler(RequestValidationError, self.handle_validation_exception)
        app.add_exception_handler(BaseBusinessException, self.handle_business_exception)
        app.add_exception_handler(Exception, self.handle_internal_server_error)

    async def handle_http_exception(self, request: Request, exc: HTTPException) -> Response:
        """处理 FastAPI/Starlette HTTPException 并返回统一响应。"""
        if 300 <= exc.status_code < 400:
            return Response(status_code=exc.status_code, headers=exc.headers)
        self._record_to_span(exc)
        error_code = ExceptionUtil.get_error_code(exc)
        msg = self._translate_message(
            request, ExceptionUtil.get_message_key(exc), ExceptionUtil.get_error_msg(exc)
        )
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error(
                "HTTP 服务端异常：{}，code：{}，msg：{}，路径：{}",
                exc.status_code,
                error_code.code,
                msg,
                self._request_route_path(request),
            )
        else:
            logger.warning(
                "HTTP 客户端异常：{}，code：{}，msg：{}，路径：{}",
                exc.status_code,
                error_code.code,
                msg,
                self._request_route_path(request),
            )
        await self._record_error(request, exc, exc.status_code, error_code, msg)
        return JSONResponse(
            status_code=200,
            content=ExceptionResponseBuilder.build(error_code, msg, exc=exc, debug=self.debug),
            headers=self._response_headers(exc.headers),
        )

    async def handle_validation_exception(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求参数校验异常并返回统一响应。"""
        self._record_to_span(exc)
        error_code = GlobalErrorCodeConstants.VALIDATION_ERROR
        msg = self._translate_message(request, error_code.message_key, error_code.description)
        details = ValidationErrorMapper.map(
            exc.errors(),
            lambda key, default, args: self._translate_message(request, key, default, args=args),
        )
        logger.warning(
            "参数校验异常：{}，路径：{}，detail：{}",
            msg,
            self._request_route_path(request),
            details.fields,
        )
        await self._record_error(
            request, exc, status.HTTP_422_UNPROCESSABLE_CONTENT, error_code, msg
        )
        return JSONResponse(
            status_code=200,
            content=ExceptionResponseBuilder.build(
                error_code, msg, error=details, exc=exc, debug=self.debug
            ),
            headers=self._response_headers(),
        )

    async def handle_business_exception(
        self, request: Request, exc: BaseBusinessException
    ) -> JSONResponse:
        """处理业务异常并记录日志、错误表和统一响应。"""
        self._record_to_span(exc)
        error_code = exc.error_code
        msg = Sanitizer.sanitize_text(exc.msg)
        message_key = exc.message_key
        # 显式提示或格式失败后的默认提示，不能再被错误码的通用翻译覆盖。
        if exc._message_translation_enabled and not exc._message_format_failed:
            msg = self._translate_message(request, message_key, msg, args=exc.format_args)
        ExceptionLogger.log(exc, error_code, msg, self._request_route_path(request))
        await self._record_error(request, exc, exc.http_status, error_code, msg)
        headers = None
        if (
            exc.retryable
            and exc.http_status == status.HTTP_429_TOO_MANY_REQUESTS
            and exc.retry_after is not None
        ):
            headers = {"Retry-After": str(exc.retry_after)}
        return JSONResponse(
            status_code=200,
            content=ExceptionResponseBuilder.build(error_code, msg, exc=exc, debug=self.debug),
            headers=self._response_headers(headers),
        )

    async def handle_internal_server_error(self, request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获异常并返回内部错误统一响应。"""
        self._record_to_span(exc)
        error_code = GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR
        msg = self._translate_message(request, error_code.message_key, error_code.description)
        ExceptionLogger.log(exc, error_code, msg, self._request_route_path(request))
        await self._record_error(
            request, exc, status.HTTP_500_INTERNAL_SERVER_ERROR, error_code, msg
        )
        return JSONResponse(
            status_code=200,
            content=ExceptionResponseBuilder.build(error_code, msg, exc=exc, debug=self.debug),
            headers=self._response_headers(),
        )

    def _response_headers(self, headers: Mapping[str, str] | None = None) -> dict[str, str]:
        """声明响应随请求语言变化，并保留认证、重试和已有 Vary 约定。"""
        result = ResponseHeaders.with_language(headers, translated=self.translator is not None)
        result["cache-control"] = "no-store"
        return result

    def _record_to_span(self, exc: Exception) -> None:
        """将异常记录到链路追踪适配器。"""
        if self.trace_reporter is None:
            return
        try:
            self.trace_reporter.on_error(exc)
        except Exception as e:
            logger.debug("异常链路追踪记录失败：{}", "".join(ExceptionTraceFormatter.format(e)))

    def _translate_message(
        self,
        request: Request,
        message_key: str | None,
        default: str | None = None,
        args: Sequence[Any] | None = None,
    ) -> str:
        """按请求上下文翻译异常消息，失败时返回兜底文案。"""
        if not message_key or self.translator is None:
            return Sanitizer.sanitize_text(default or message_key or "")
        try:
            return Sanitizer.sanitize_text(
                self.translator.translate_any_scope(
                    message_key,
                    request.headers.get("Accept-Language"),
                    default=default,
                    args=args,
                )
            )
        except Exception as e:
            logger.warning(
                "异常文案翻译失败：{}，{}",
                Sanitizer.sanitize_text(message_key),
                "".join(ExceptionTraceFormatter.format(e)),
            )
            return Sanitizer.sanitize_text(default or message_key)

    async def _record_error(
        self,
        request: Request,
        exc: Exception,
        status_code: int,
        error_code: ErrorCode,
        msg: str,
    ) -> None:
        """由当前应用的记录器统一处理需要持久化的诊断事件。"""
        if self.error_recorder is not None and self._should_record_error(exc, status_code):
            await self.error_recorder.record(request, exc, error_code, msg)

    @staticmethod
    def _should_record_error(exc: Exception, status_code: int) -> bool:
        """判定异常是否需写入系统异常表：5xx 默认入库，4xx 仅在业务异常显式开启 record_error 时入库。"""
        if status.HTTP_500_INTERNAL_SERVER_ERROR <= status_code < 600:
            return True
        return isinstance(exc, BaseBusinessException) and exc.record_error

    @staticmethod
    def _request_route_path(request: Request) -> str:
        """仅记录低基数路由模板，避免 URL capability 进入异常日志。"""
        route = request.scope.get("route")
        return str(route.path) if route is not None else "<unmatched>"
