import re

from framework.starter_i18n.core.i18n_options import I18nOptions


class AcceptLanguageParser:
    """按 HTTP 权重选择配置中的语言标签。

    exact 仅接受完整标签，primary 额外允许主语言匹配；同权重按请求顺序选择。
    更具体的 q=0 排除项优先于通配符，非法项忽略，无可用候选时返回配置默认语言。
    """

    _TAG = re.compile(r"[a-z]{1,8}(?:-[a-z0-9]{1,8})*")
    _QUALITY = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)")

    def __init__(self, options: I18nOptions) -> None:
        """保存已经校验的语言选择配置。"""
        self.options = options

    def detect_lang(self, accept_language: str | None) -> str:
        """按具体程度确定每种语言的权重，再按偏好和原顺序选择。"""
        candidates = self._parse(accept_language or "")
        ranked: list[tuple[float, int, int, str]] = []
        for locale_order, locale in enumerate(self.options.supported_locales):
            matches = []
            for order, (tag, quality) in enumerate(candidates):
                specificity = self._specificity(tag, locale.casefold())
                if specificity is not None:
                    matches.append((specificity, quality, -order))
            if matches:
                _, quality, negative_order = max(matches)
                if quality > 0:
                    ranked.append((quality, negative_order, -locale_order, locale))
        return max(ranked)[3] if ranked else self.options.default_locale

    def _specificity(self, tag: str, locale: str) -> int | None:
        """区分精确标签、主语言和通配符，保证排除规则不被宽匹配覆盖。"""
        if tag == "*":
            return -1
        if tag == locale:
            return len(tag.split("-")) + 1
        if self.options.match_mode == "primary":
            if locale.startswith(tag + "-"):
                return len(tag.split("-"))
            if tag.partition("-")[0] == locale.partition("-")[0]:
                return 0
        return None

    @classmethod
    def _parse(cls, header: str) -> list[tuple[str, float]]:
        """解析合法语言项和 q，不把 NaN、越界权重或未知参数当作默认权重。"""
        candidates: list[tuple[str, float]] = []
        for item in header.split(","):
            parts = [part.strip() for part in item.split(";")]
            tag = parts[0].casefold()
            if tag != "*" and cls._TAG.fullmatch(tag) is None:
                continue
            quality = 1.0
            if len(parts) > 1:
                if len(parts) != 2:
                    continue
                name, separator, value = parts[1].partition("=")
                if separator != "=" or name.strip().casefold() != "q":
                    continue
                value = value.strip()
                if cls._QUALITY.fullmatch(value) is None:
                    continue
                quality = float(value)
            candidates.append((tag, quality))
        return candidates
