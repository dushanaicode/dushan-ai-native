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
    issuer_pattern: str | None = None
    # 授权码流程中 nonce 是可选声明（OpenID Connect Core 3.1.2.1）；个别厂商不回传，
    # 只有在渠道确认不回传时才置 False，仍然比对已出现的 nonce，不接受任意值。
    nonce_supported: bool = True

    def __post_init__(self):
        allowed = {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
        if not self.algorithms or not set(self.algorithms).issubset(allowed):
            raise ValueError("OIDC 只允许明确配置的非对称签名算法")
