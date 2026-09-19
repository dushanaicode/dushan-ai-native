import json
from http.cookiejar import CookieJar

import httpx

from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.core.auth_cookie_policy import AuthCookiePolicy
from framework.starter_auth.core.auth_http_log_filter import AuthHttpLogFilter
from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException


class AuthHttpClient:
    """由 AuthService 打开和排空的唯一 HTTP 资源，固定目的地址且不重试。"""

    def __init__(self, settings: AuthSettings, *, transport=None):
        self.settings = settings
        self._guard = AuthHttpLogFilter()
        self.client = httpx.AsyncClient(
            transport=transport,
            proxy=settings.proxy,
            trust_env=False,
            follow_redirects=False,
            timeout=settings.http_timeout_seconds,
            limits=httpx.Limits(max_connections=settings.max_connections),
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            cookies=CookieJar(policy=AuthCookiePolicy()),
        )
        self._guard.open()

    async def request(self, method: str, url: str, *, effect: bool = False, **kwargs) -> bytes:
        AuthUrlPolicy.require(url, allow_loopback_http=self.settings.allow_loopback_http)
        outcome = "unknown" if effect else "not_sent"
        try:
            with self._guard.quiet():
                async with self.client.stream(method, url, **kwargs) as response:
                    if not 200 <= response.status_code < 300:
                        raise AuthException(
                            Codes.REJECTED if 400 <= response.status_code < 500 else Codes.NETWORK,
                            outcome="rejected" if 400 <= response.status_code < 500 else outcome,
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise AuthException(Codes.RESPONSE, outcome=outcome)
                    data = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if len(data) + len(chunk) > self.settings.max_response_bytes:
                            raise AuthException(Codes.RESPONSE, outcome=outcome)
                        data.extend(chunk)
                    return bytes(data)
        except (httpx.PoolTimeout, httpx.ConnectTimeout, httpx.ConnectError) as error:
            raise AuthException(Codes.NETWORK, cause=error) from error
        except httpx.TimeoutException as error:
            raise AuthException(Codes.TIMEOUT, outcome=outcome, cause=error) from error
        except httpx.RequestError as error:
            raise AuthException(Codes.NETWORK, outcome=outcome, cause=error) from error

    async def json(self, method: str, url: str, *, effect=False, **kwargs) -> dict:
        content = await self.request(method, url, effect=effect, **kwargs)
        return self.decode_json(content, effect=effect)

    @classmethod
    def decode_json(cls, content: bytes | str, *, effect=False) -> dict:
        try:
            result = json.loads(content, object_pairs_hook=cls.unique_object)
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, UnicodeError, RecursionError) as error:
            raise AuthException(
                Codes.RESPONSE,
                outcome="unknown" if effect else "not_sent",
                cause=error,
            ) from error

    @staticmethod
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("第三方 JSON 含重复字段")
            result[key] = value
        return result

    async def close(self):
        try:
            with self._guard.quiet():
                await self.client.aclose()
        finally:
            self._guard.close()
