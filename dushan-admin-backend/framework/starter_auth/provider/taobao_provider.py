from urllib.parse import unquote

from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class TaobaoProvider(OAuthProvider):
    capabilities = (ProviderCapability("TAOBAO", refresh=True),)
    authorization_endpoint = "https://oauth.taobao.com/authorize"
    token_endpoint = "https://oauth.taobao.com/token"
    fixed_scopes = ()

    def authorization_parameters(self):
        return {**super().authorization_parameters(), "view": "web"}

    def token(self, data, **values):
        Payload.reject_errors(data)
        # 两种身份字段由淘宝实际应用权限决定，分别保留来源种类，不能静默混合。
        name = "taobao_user_id" if data.get("taobao_user_id") is not None else "taobao_open_uid"
        subject = Payload.identifier(data, name)
        return super().token(data, subject=subject, subject_type=name, **values)

    async def userinfo(self, tokens):
        nickname = unquote(Payload.text(tokens.data, "taobao_user_nick", required=True))
        return self.identity(
            {},
            tokens.subject,
            subject_type=tokens.subject_type,
            username=nickname,
            nickname=nickname,
        )
