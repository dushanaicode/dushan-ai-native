import hashlib
import re
import secrets

from framework.starter_security.exception.security_exception import SecurityException


class OpaqueToken:
    """本站随机令牌；签发结果只交付一次，存储与查询只使用摘要。"""

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def digest(token: str) -> str:
        if not isinstance(token, str) or re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token) is None:
            raise SecurityException("invalid")
        return hashlib.sha256(token.encode("ascii")).hexdigest()
