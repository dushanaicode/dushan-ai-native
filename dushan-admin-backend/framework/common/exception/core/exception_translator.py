from collections.abc import Sequence
from typing import Protocol


class ExceptionTranslator(Protocol):
    """约定异常消息的翻译入口，由应用装配时提供实现。

    传入 GlobalExceptionHandler(translator=...)，按请求语言查询消息。
    返回值应为可公开的文本，default 用于缺少翻译时的中文提示。
    """

    def translate_any_scope(
        self,
        message_key: str,
        accept_language: str | None,
        *,
        default: str | None = None,
        args: Sequence[object] | None = None,
    ) -> str:
        """返回匹配语言和参数的消息，缺少翻译时使用默认提示。"""
        ...
