from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class MiniProgramProvider(AuthProvider):
    """微信小程序与 QQ 小程序 code2session 适配器。

    官方资料：
    - 微信接口: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
    - QQ 互联: https://connect.qq.com/
    实现端点：
    - wechat: https://api.weixin.qq.com/sns/jscode2session
    - qq: https://api.q.qq.com/sns/jscode2session
    """

    subject_field = "openid"
    capabilities = tuple(
        ProviderCapability(source, mode="native", token_kind="session_key")
        for source in ("WECHAT_MINI_PROGRAM", "QQ_MINI_PROGRAM")
    )
    fixed_scopes = ()

    async def exchange(self, code, flow):
        url = (
            "https://api.weixin.qq.com/sns/jscode2session"
            if self.config.source == "WECHAT_MINI_PROGRAM"
            else "https://api.q.qq.com/sns/jscode2session"
        )
        data = await self.http.json(
            "GET",
            url,
            effect=True,
            params={
                "appid": self.config.client_id,
                "secret": self.config.client_secret.get_secret_value(),
                "js_code": code,
                "grant_type": "authorization_code",
            },
        )
        Payload.reject_errors(data)
        return self.tokens(
            session_key=Payload.text(data, "session_key", required=True),
            subject=Payload.text(data, "openid", required=True),
            union_id=Payload.text(data, "unionid"),
        )

    async def userinfo(self, tokens):
        # code2session 不返回头像/昵称，也不把 session_key 伪装成 OAuth access_token。
        return self.identity({}, tokens.subject, union_id=tokens.union_id)
