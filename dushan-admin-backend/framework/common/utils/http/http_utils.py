import base64
import binascii
import re
from collections.abc import Mapping
from http.cookies import SimpleCookie
from urllib.parse import parse_qsl, unquote_to_bytes, urlencode, urlsplit, urlunsplit

from fastapi import Request
from fastapi.exceptions import RequestValidationError

from framework.common.utils.request.request_utils import QueryParams, RequestUtils

type QueryScalar = str | int | float | bool
type QueryValue = QueryScalar | list[QueryScalar] | tuple[QueryScalar, ...]


class HttpUtils:
    """处理 URL、OAuth2 Basic 凭据和查询参数，不发起网络请求。"""

    @staticmethod
    def replace_url_query(url: str, key: str, value: str | int) -> str:
        """替换指定参数，保留其他重复参数、空值和片段。"""
        parts = urlsplit(url)
        pairs = [
            (name, item)
            for name, item in parse_qsl(parts.query, keep_blank_values=True)
            if name != key
        ]
        pairs.append((key, str(value)))
        return urlunsplit(parts._replace(query=urlencode(pairs)))

    @staticmethod
    def append_query(
        base: str,
        query: Mapping[str, QueryValue],
        keys_map: Mapping[str, str] | None = None,
        to_fragment: bool = False,
    ) -> str:
        """将给定键合入 query 或纯参数 fragment，同名旧键由新值替换。"""
        mapped = {}
        for key, value in query.items():
            target = key if keys_map is None else keys_map.get(key, key)
            if target in mapped:
                raise ValueError("查询参数映射后重名")
            mapped[target] = value
        parts = urlsplit(base)
        source = parts.fragment if to_fragment else parts.query
        old = [
            (key, value)
            for key, value in parse_qsl(source, keep_blank_values=True)
            if key not in mapped
        ]
        encoded = urlencode(old)
        added = urlencode(mapped, doseq=True)
        result = "&".join(part for part in (encoded, added) if part)
        return urlunsplit(
            parts._replace(fragment=result) if to_fragment else parts._replace(query=result)
        )

    @classmethod
    def build_url(
        cls, base: str, path: str = "", query_params: Mapping[str, QueryValue] | None = None
    ) -> str:
        """拼接路径并合入查询参数，fragment 始终位于 URL 末尾。"""
        parts = urlsplit(base)
        if path:
            parts = parts._replace(path=parts.path.rstrip("/") + "/" + path.lstrip("/"))
        url = urlunsplit(parts)
        return url if query_params is None else cls.append_query(url, query_params)

    @classmethod
    def obtain_basic_authorization(cls, request: Request) -> tuple[str, str] | None:
        """按 OAuth2 client_secret_basic 解析凭据；缺失或非法凭据均不通过认证。"""
        header = request.headers.get("Authorization")
        if header is None:
            return None
        scheme, separator, encoded = header.partition(" ")
        if not separator or scheme.lower() != "basic":
            return None
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            client, separator, secret = decoded.partition(":")
            if not separator:
                return None
            return cls._decode_form_component(client), cls._decode_form_component(secret)
        except (binascii.Error, ValueError):
            return None

    @staticmethod
    def _decode_form_component(value: str) -> str:
        """严格解码表单组件，不接受残缺的百分号转义。"""
        if re.search(r"%(?![0-9A-Fa-f]{2})", value):
            raise ValueError("非法百分号转义")
        return unquote_to_bytes(value.replace("+", " ")).decode("utf-8")

    @staticmethod
    def parse_cookie_string(value: str) -> dict[str, str]:
        """用标准库读取 Cookie，包括引号包裹的值。"""
        cookie = SimpleCookie()
        cookie.load(value)
        return {key: item.value for key, item in cookie.items()}

    @staticmethod
    def preprocess_array_query_params(request: Request) -> QueryParams:
        """将 ids[2]、ids[0] 按索引升序合并，拒绝同名混用和重复索引。"""
        result = RequestUtils.get_query_params(request)
        arrays: dict[str, dict[str, str]] = {}
        for key, value in request.query_params.multi_items():
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[(0|[1-9][0-9]*)\]", key)
            if match is None:
                continue
            name, index_text = match.groups()
            items = arrays.setdefault(name, {})
            if name in request.query_params or index_text in items:
                raise RequestValidationError(
                    [
                        {
                            "type": "value_error",
                            "loc": ("query", name),
                            "msg": "数组参数不能混用格式或重复索引",
                            "input": None,
                        }
                    ]
                )
            items[index_text] = value
            result.pop(key, None)
        result.update(
            {
                name: [
                    items[index] for index in sorted(items, key=lambda index: (len(index), index))
                ]
                for name, items in arrays.items()
            }
        )
        return result
