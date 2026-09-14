from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OidcMetadata:
    """由受信任 Provider 声明，Token header 和用户输入无权修改地址及算法。"""

    issuer: str
    jwks_uri: str
    algorithms: tuple[str, ...]
    authorization_endpoint: str
    token_endpoint: str
    discovery_uri: str | None = None

    def __post_init__(self):
        allowed = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
        if not self.algorithms or not set(self.algorithms).issubset(allowed):
            raise ValueError("OIDC 只允许明确配置的非对称签名算法")
