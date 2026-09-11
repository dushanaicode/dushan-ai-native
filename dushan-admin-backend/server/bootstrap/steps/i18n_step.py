from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from framework.common.exception.constants.global_error_code_constants import (
    GlobalErrorCodeConstants,
)
from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.utils.validation_error_mapper import ValidationErrorMapper
from framework.common.i18n.starter.i18n_starter import I18nStarter
from server.bootstrap.context import AppBootstrapContext


class I18nStep:
    """加载当前应用的翻译资源，供异常处理器和中间件响应共用。"""

    @staticmethod
    @asynccontextmanager
    async def run(ctx: AppBootstrapContext) -> AsyncIterator[None]:
        """校验公共错误码的翻译，退出时释放当前应用的翻译器引用。"""
        message_keys = tuple(
            value.message_key
            for value in vars(GlobalErrorCodeConstants).values()
            if isinstance(value, ErrorCode)
        )
        message_keys += tuple(f"validation.{key}" for key in ValidationErrorMapper.messages)
        translator = I18nStarter.initialize(
            ctx.i18n_options, base_dir=ctx.base_dir, message_keys=message_keys
        )
        ctx.exception_handler.translator = translator
        ctx.middleware_result.translator = translator
        try:
            yield
        finally:
            ctx.exception_handler.translator = None
            ctx.middleware_result.translator = None
