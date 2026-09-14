import ipaddress
from urllib.parse import urlsplit

from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException


class AuthUrlPolicy:
    @staticmethod
    def require(
        url: str, *, allow_loopback_http: bool, query: bool = False, fragment: bool = False
    ) -> None:
        if not isinstance(url, str):
            raise AuthException(Codes.CONFIG)
        try:
            parsed = urlsplit(url)
            host, port = parsed.hostname, parsed.port
            if (
                not url
                or len(url) > 2048
                or not url.isascii()
                or any(ord(c) <= 32 or ord(c) == 127 for c in url)
                or "\\" in url
                or not host
                or "%" in host
                or port == 0
                or parsed.username is not None
                or (parsed.fragment and not fragment)
                or (parsed.query and not query)
            ):
                raise ValueError
            if parsed.scheme == "https":
                return
            if allow_loopback_http and parsed.scheme == "http":
                if host == "localhost" or ipaddress.ip_address(host).is_loopback:
                    return
        except ValueError:
            pass
        raise AuthException(Codes.CONFIG)
