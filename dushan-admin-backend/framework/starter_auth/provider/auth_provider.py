from abc import ABC, abstractmethod
from urllib.parse import urlencode

from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.exception.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.auth_flow import AuthFlow
from framework.starter_auth.model.auth_tokens import AuthTokens
from framework.starter_auth.model.external_identity import ExternalIdentity
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class AuthProvider(ABC):
    """授权源扩展契约。实例只持有本次配置；连接和共享状态由所属应用提供。"""

    capabilities = ()
    authorization_endpoint = ""
    token_endpoint = ""
    userinfo_endpoint = ""
    refresh_endpoint = ""
    revoke_endpoint = ""
    callback_code = "code"
    allowed_options = frozenset()
    required_options = frozenset()
    required_credentials = frozenset()
    fixed_scopes = None
    scope_separator = " "
    client_parameter = "client_id"
    profile_fields = {}
    oidc_metadata = None
    expires_required = True
    subject_field = "id"
    ENDPOINT_FIELDS = (
        "authorization_endpoint",
        "token_endpoint",
        "userinfo_endpoint",
        "refresh_endpoint",
        "revoke_endpoint",
    )

    def __init__(self, config: AuthClientConfig, http, credentials, oidc):
        self.config, self.http, self.credentials, self.oidc = config, http, credentials, oidc
        self.capability = next(c for c in self.capabilities if c.source == config.source)

    @classmethod
    def validate_client(cls, config: AuthClientConfig, settings: AuthSettings):
        capability = next(c for c in cls.capabilities if c.source == config.source)
        if (
            set(config.options) - cls.allowed_options
            or cls.required_options - config.options.keys()
        ):
            raise AuthException(Codes.CONFIG)
        if set(config.credentials) != cls.required_credentials:
            raise AuthException(Codes.CONFIG)
        if any(not value for value in config.options.values()):
            raise AuthException(Codes.CONFIG)
        if any(not value.get_secret_value() for value in config.credentials.values()):
            raise AuthException(Codes.CONFIG)
        if config.pkce != capability.pkce:
            raise AuthException(Codes.CONFIG)
        if capability.mode == "browser":
            if config.redirect_uri is None:
                raise AuthException(Codes.CONFIG)
            AuthUrlPolicy.require(
                config.redirect_uri,
                allow_loopback_http=settings.allow_loopback_http,
                query=True,
            )
        elif config.redirect_uri is not None:
            raise AuthException(Codes.CONFIG)
        if cls.fixed_scopes is not None and config.scopes != cls.fixed_scopes:
            raise AuthException(Codes.CONFIG)
        if capability.oidc and "openid" not in config.scopes:
            raise AuthException(Codes.CONFIG)

    def validate_endpoints(self, settings: AuthSettings) -> None:
        """校验已解析的渠道地址，包括依赖本次客户端配置的动态属性。"""
        if self.capability.mode == "browser" and not self.authorization_endpoint:
            raise AuthException(Codes.CONFIG)
        for name in self.ENDPOINT_FIELDS:
            endpoint = getattr(self, name)
            if not isinstance(endpoint, str):
                raise AuthException(Codes.CONFIG)
            if endpoint:
                AuthUrlPolicy.require(endpoint, allow_loopback_http=settings.allow_loopback_http)

    def authorization_parameters(self):
        return {
            "response_type": "code",
            self.client_parameter: self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.scope_separator.join(self.config.scopes),
        }

    def authorize(self, flow: AuthFlow, challenge: str):
        if self.capability.mode != "browser":
            raise AuthException(Codes.UNSUPPORTED)
        parameters = self.authorization_parameters()
        parameters["state"] = flow.state
        if self.capability.pkce:
            parameters.update(code_challenge=challenge, code_challenge_method="S256")
        if self.capability.oidc:
            parameters["nonce"] = flow.nonce
        return self.authorization_endpoint + "?" + urlencode(parameters)

    @abstractmethod
    async def exchange(self, code, flow) -> AuthTokens:
        pass

    @abstractmethod
    async def userinfo(self, tokens) -> ExternalIdentity:
        pass

    async def refresh(self, tokens) -> AuthTokens:
        raise AuthException(Codes.UNSUPPORTED)

    async def revoke(self, tokens) -> None:
        raise AuthException(Codes.UNSUPPORTED)

    def token(self, data, **values):
        Payload.reject_errors(data)
        fields = {
            "access_token": Payload.text(data, "access_token", required=True),
            "refresh_token": Payload.text(data, "refresh_token"),
            "id_token": Payload.text(data, "id_token"),
            "expires_in": Payload.integer(data, "expires_in", required=self.expires_required),
            "token_type": Payload.text(data, "token_type"),
            "scope": Payload.text(data, "scope"),
        }
        fields.update(values)
        return self.tokens(data=data, **fields)

    def tokens(self, **values):
        if values.get("subject") is not None:
            values.setdefault("subject_type", self.subject_field)
        return AuthTokens(
            application_id=self.config.application_id,
            source=self.config.source,
            client_id=self.config.client_id,
            **values,
        )

    def identity(self, data, subject, **values):
        fields = {
            target: Payload.text(data, source) for target, source in self.profile_fields.items()
        }
        fields.update(values)
        fields.setdefault("subject_type", self.subject_field)
        return ExternalIdentity(
            application_id=self.config.application_id,
            source=self.config.source,
            client_id=self.config.client_id,
            subject=subject,
            raw=data,
            **fields,
        )

    def validate_tokens(
        self, tokens: AuthTokens, *, oidc_exchange: bool = False, outcome="unknown"
    ) -> None:
        """凭据类型是执行契约，身份交换和 session_key 不接受 OAuth 凭据混入。"""
        if not isinstance(tokens, AuthTokens):
            raise AuthException(Codes.RESPONSE, outcome=outcome)
        kind = self.capability.token_kind
        if kind == "access_token":
            valid = tokens.access_token is not None and tokens.session_key is None
        elif kind == "session_key":
            valid = (
                tokens.session_key is not None
                and tokens.subject is not None
                and all(
                    value is None
                    for value in (tokens.access_token, tokens.refresh_token, tokens.id_token)
                )
            )
        else:
            valid = tokens.subject is not None and all(
                value is None
                for value in (
                    tokens.access_token,
                    tokens.refresh_token,
                    tokens.id_token,
                    tokens.session_key,
                )
            )
        if not valid:
            raise AuthException(Codes.RESPONSE, outcome=outcome)
        if (
            oidc_exchange
            and self.capability.oidc
            and (tokens.id_token is None or tokens.claims is None)
        ):
            raise AuthException(Codes.OIDC, outcome=outcome)

    @staticmethod
    def access(tokens):
        if tokens.access_token is None:
            raise AuthException(Codes.INPUT)
        return tokens.access_token.get_secret_value()

    @staticmethod
    def refresh_value(tokens):
        if tokens.refresh_token is None:
            raise AuthException(Codes.INPUT)
        return tokens.refresh_token.get_secret_value()
