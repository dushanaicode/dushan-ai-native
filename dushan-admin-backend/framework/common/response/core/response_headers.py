from collections.abc import Mapping


class ResponseHeaders:
    """合并标准响应头语义，供异常处理器与中间件共用。"""

    @staticmethod
    def with_language(
        headers: Mapping[str, str] | None = None, *, translated: bool = False
    ) -> dict[str, str]:
        """规范化头名称并合并 Vary，保留认证、重试及通配符语义。"""
        result = {name.lower(): value for name, value in (headers or {}).items()}
        if translated:
            fields = [item.strip() for item in result.get("vary", "").split(",") if item.strip()]
            if not any(field == "*" or field.lower() == "accept-language" for field in fields):
                fields.append("Accept-Language")
            result["vary"] = ", ".join(fields)
        return result
