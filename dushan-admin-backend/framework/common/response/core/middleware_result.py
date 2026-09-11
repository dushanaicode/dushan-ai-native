from collections.abc import Mapping
from typing import Any

from fastapi.responses import JSONResponse
from loguru import logger
from starlette.types import Send

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.core.error_details import ErrorDetails
from framework.common.exception.core.exception_translator import ExceptionTranslator
from framework.common.exception.utils.response_builder import ExceptionResponseBuilder
from framework.common.response.core.response_headers import ResponseHeaders


class MiddlewareResult:
    """为中间件生成统一错误响应，显式持有当前应用的翻译与调试配置。

    error_response 与 send_error 使用同一个 JSONResponse 编码结果。
    普通业务错误统一HTTP 200；记录和严重性仍由异常处理层按原分类处理。
    """

    def __init__(
        self, translator: ExceptionTranslator | None = None, *, debug: bool = False
    ) -> None:
        """保存实例依赖，拒绝会意外开启诊断输出的非布尔调试值。"""
        if type(debug) is not bool:
            raise TypeError("debug 必须是布尔值")
        self.translator = translator
        self.debug = debug

    def build_error_content(
        self,
        error_code: ErrorCode | None = None,
        message: str | None = None,
        data: Any = None,
        exc: Exception | None = None,
        *,
        error: ErrorDetails | None = None,
        accept_language: str | None = None,
    ) -> dict[str, Any]:
        """生成脱敏错误体；显式message为最终文案，翻译失败保留默认提示。"""
        definition = (
            GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR if error_code is None else error_code
        )
        self._validate_error_code(definition)
        resolved_message = message if message is not None else definition.description
        if message is None and self.translator is not None:
            try:
                resolved_message = self.translator.translate_any_scope(
                    definition.message_key, accept_language, default=resolved_message
                )
            except Exception as translation_error:
                logger.warning(
                    "中间件错误文案翻译失败：{}",
                    "".join(ExceptionTraceFormatter.format(translation_error)),
                )
        return ExceptionResponseBuilder.build(
            definition, resolved_message, data, exc, error=error, debug=self.debug
        )

    def error_response(
        self,
        error_code: ErrorCode | None = None,
        message: str | None = None,
        data: Any = None,
        exc: Exception | None = None,
        *,
        error: ErrorDetails | None = None,
        accept_language: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JSONResponse:
        """生成JSON错误响应，保留HTTP头并声明语言差异。"""
        definition = (
            GlobalErrorCodeConstants.INTERNAL_SERVER_ERROR if error_code is None else error_code
        )
        response_headers = ResponseHeaders.with_language(
            headers, translated=self.translator is not None
        )
        response_headers["cache-control"] = "no-store"
        return JSONResponse(
            status_code=200,
            content=self.build_error_content(
                definition, message, data, exc, error=error, accept_language=accept_language
            ),
            headers=response_headers,
        )

    async def send_error(
        self,
        send: Send,
        error_code: ErrorCode | None = None,
        message: str | None = None,
        data: Any = None,
        exc: Exception | None = None,
        *,
        error: ErrorDetails | None = None,
        accept_language: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """在尚未开始响应时发送同一编码结果，不另建一套字节序列化逻辑。"""
        response = self.error_response(
            error_code,
            message,
            data,
            exc,
            error=error,
            accept_language=accept_language,
            headers=headers,
        )
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": response.raw_headers,
            }
        )
        await send({"type": "http.response.body", "body": response.body, "more_body": False})

    @staticmethod
    def _validate_error_code(error_code: ErrorCode) -> None:
        """错误入口拒绝成功码和非错误分类，不改变定义中的内部分类。"""
        status = error_code.http_status if error_code.http_status is not None else 400
        if error_code.code == GlobalErrorCodeConstants.SUCCESS.code or not 400 <= status <= 599:
            raise ValueError("中间件错误响应必须使用错误码与4xx/5xx状态")
