import re


class SerializedSensitiveValueSanitizer:
    """清理 Python/JSON 序列化文本中已知敏感 key 对应的单个 value。"""

    _EXCEPTION_CHAIN_BOUNDARY_PATTERN = re.compile(
        r"\r?\n(?:\r?\n)?(?:"
        r"The above exception was the direct cause of the following exception:|"
        r"During handling of the above exception, another exception occurred:|"
        r"Traceback \(most recent call last\):|"
        r"\s*\+(?:-\+)?-+\s+\d+\s+-+"
        r")"
    )

    @classmethod
    def sanitize(cls, value: str, sensitive_key_pattern: re.Pattern[str]) -> str:
        """遮盖命中的序列化字段值，并保留字段外的原始文本。"""
        chunks: list[str] = []
        cursor = 0
        for match in sensitive_key_pattern.finditer(value):
            if match.start() < cursor:
                continue
            value_start = match.end()
            while value_start < len(value) and value[value_start].isspace():
                value_start += 1
            value_end = cls._find_serialized_value_end(value, value_start)
            chunks.append(value[cursor:value_start])
            chunks.append(cls._redacted_serialized_value(value, value_start))
            cursor = value_end
        if not chunks:
            return value
        chunks.append(value[cursor:])
        return "".join(chunks)

    @classmethod
    def _find_serialized_value_end(cls, value: str, start: int) -> int:
        """根据引号、字节串或括号结构定位字段值末尾。"""
        if start >= len(value):
            return start
        if value[start] in "\"'":
            return cls._find_quoted_value_end(value, start)
        if value[start] in "bB" and start + 1 < len(value) and value[start + 1] in "\"'":
            return cls._find_quoted_value_end(value, start + 1)
        if value[start] in "[({":
            return cls._find_balanced_value_end(value, start)
        end = start
        while end < len(value) and value[end] not in ",;}\r\n":
            end += 1
        return end

    @staticmethod
    def _find_quoted_value_end(value: str, quote_start: int) -> int:
        """跳过转义引号，遇到未闭合的单行字符串时在行尾停止。"""
        quote = value[quote_start]
        escaped = False
        for index in range(quote_start + 1, len(value)):
            current = value[index]
            if current in "\r\n" and not escaped:
                return index
            next_quote, escaped = SerializedSensitiveValueSanitizer._advance_quote_state(
                current,
                quote,
                escaped,
            )
            if next_quote is None:
                return index + 1
        return len(value)

    @classmethod
    def _find_balanced_value_end(cls, value: str, start: int) -> int:
        """匹配嵌套括号，未闭合时保留后续异常链或异常组分支。"""
        closing = {"[": "]", "(": ")", "{": "}"}
        stack = [closing[value[start]]]
        quote: str | None = None
        escaped = False
        boundary = cls._EXCEPTION_CHAIN_BOUNDARY_PATTERN.search(value, start + 1)
        search_end = boundary.start() if boundary is not None else len(value)
        for index in range(start + 1, search_end):
            current = value[index]
            if quote is not None:
                quote, escaped = cls._advance_quote_state(current, quote, escaped)
                continue
            if current in "\"'":
                quote = current
                continue
            if current in closing:
                stack.append(closing[current])
                continue
            if current != stack[-1]:
                continue
            stack.pop()
            if not stack:
                return index + 1
        return search_end

    @staticmethod
    def _advance_quote_state(current: str, quote: str, escaped: bool) -> tuple[str | None, bool]:
        """按当前字符更新引号和转义状态。"""
        if escaped:
            return quote, False
        if current == "\\":
            return quote, True
        if current == quote:
            return None, False
        return quote, False

    @staticmethod
    def _redacted_serialized_value(value: str, start: int) -> str:
        """生成遮盖文本并保留原有字符串或字节串引号。"""
        if start >= len(value):
            return "***"
        if value[start] in "\"'":
            return f"{value[start]}***{value[start]}"
        if value[start] in "bB" and start + 1 < len(value) and value[start + 1] in "\"'":
            return f"{value[start : start + 2]}***{value[start + 1]}"
        return "***"
