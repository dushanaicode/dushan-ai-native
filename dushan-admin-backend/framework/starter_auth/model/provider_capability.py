from dataclasses import dataclass
from typing import Literal

AUTH_SOURCE_PATTERN = r"^[A-Z][A-Z0-9_]{0,63}$"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """能力声明描述协议事实；session_key 和直接身份交换不冒充 access_token。"""

    source: str
    mode: Literal["browser", "native"] = "browser"
    token_kind: Literal["access_token", "session_key", "identity"] = "access_token"
    pkce: bool = False
    oidc: bool = False
    refresh: bool = False
    refresh_rotation: bool = False
    revoke: bool = False
