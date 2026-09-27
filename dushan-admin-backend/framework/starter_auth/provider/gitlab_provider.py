from framework.starter_auth.core.auth_url_policy import AuthUrlPolicy
from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class GitlabProvider(OAuthProvider):
    """GitLab OAuth 2.0，支持 GitLab.com 与自建 GitLab。

    官方资料：
    - OAuth API: https://docs.gitlab.com/api/oauth2/
    - GitLab.com Discovery: https://gitlab.com/.well-known/openid-configuration
    自建实例的 `base_url` 指向实例根地址，端点按同一 OAuth 路径构造。
    """

    subject_field = "id"
    # 刷新会同时作废旧的 access_token 与 refresh_token，响应必须带回新的 refresh_token。
    capabilities = (ProviderCapability("GITLAB", pkce=True, refresh=True, refresh_rotation=True),)
    allowed_options = frozenset(("base_url",))
    fixed_scopes = ("read_user",)
    profile_fields = {
        "username": "username",
        "nickname": "name",
        "avatar": "avatar_url",
        "email": "email",
        "blog": "web_url",
    }

    @staticmethod
    def _base_url(value: str | None) -> str:
        return "https://gitlab.com" if value is None else value.rstrip("/")

    @property
    def authorization_endpoint(self) -> str:
        return self._base_url(self.config.options.get("base_url")) + "/oauth/authorize"

    @property
    def token_endpoint(self) -> str:
        return self._base_url(self.config.options.get("base_url")) + "/oauth/token"

    @property
    def userinfo_endpoint(self) -> str:
        return self._base_url(self.config.options.get("base_url")) + "/api/v4/user"

    @property
    def refresh_endpoint(self) -> str:
        return self.token_endpoint

    @classmethod
    def validate_client(cls, config, settings):
        super().validate_client(config, settings)
        base_url = cls._base_url(config.options.get("base_url"))
        try:
            AuthUrlPolicy.require(base_url, allow_loopback_http=settings.allow_loopback_http)
        except AuthException:
            raise
        except Exception as error:
            raise AuthException(Codes.CONFIG, cause=error) from error

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"Authorization": "Bearer " + self.access(tokens)},
        )
        Payload.reject_errors(data)
        return self.identity(data, Payload.identifier(data, "id"))
