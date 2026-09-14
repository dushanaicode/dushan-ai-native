import re
from unicodedata import category

import nh3


class RichTextSanitizer:
    """显式净化 HTML 内容片段；不能用作 HTML 属性、脚本、SVG 或 CSS 上下文的转义器。"""

    _tags = frozenset(
        {
            "a",
            "blockquote",
            "br",
            "code",
            "em",
            "h1",
            "h2",
            "h3",
            "h4",
            "hr",
            "img",
            "li",
            "mark",
            "ol",
            "p",
            "pre",
            "s",
            "span",
            "strong",
            "sub",
            "sup",
            "table",
            "tbody",
            "td",
            "tfoot",
            "th",
            "thead",
            "tr",
            "u",
            "ul",
        }
    )
    _attributes = {
        "a": frozenset({"href", "title"}),
        "img": frozenset({"alt", "height", "src", "title", "width"}),
        **{tag: frozenset({"style"}) for tag in ("h1", "h2", "h3", "h4", "mark", "p", "span")},
    }
    _data_image = re.compile(r"data:image/(?:gif|jpeg|png|webp);base64,[a-z0-9+/=\s]+", re.I)

    @classmethod
    def clean(cls, value: str) -> str:
        return nh3.clean(
            value,
            tags=set(cls._tags),
            attributes={
                "*": {"class"},
                **{tag: set(names) for tag, names in cls._attributes.items()},
            },
            attribute_filter=cls._filter_attribute,
            url_schemes={"data", "http", "https", "mailto", "tel"},
            filter_style_properties={"background-color", "color", "text-align"},
            strip_comments=True,
        )

    @classmethod
    def _filter_attribute(cls, tag: str, name: str, value: str) -> str | None:
        if name in {"href", "src"} and any(category(char) in {"Cc", "Cf"} for char in value):
            # URL 解析器可能把含不可见字符的伪协议当相对路径，不能把它留给浏览器解释。
            return None
        normalized = value.strip()
        if tag == "a" and name == "href" and normalized.lower().startswith("data:"):
            return None
        if tag == "img" and name == "src" and normalized.lower().startswith("data:"):
            return value if cls._data_image.fullmatch(normalized) else None
        return value
