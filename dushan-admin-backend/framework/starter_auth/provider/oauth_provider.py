from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException
from framework.starter_auth.provider.auth_provider import AuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class OAuthProvider(AuthProvider):
    """共享 OAuth 授权码/刷新表单，特殊渠道只覆写真正不同的协议步骤。"""

    subject_field = "id"

    def client_fields(self):
        return {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret.get_secret_value(),
        }

    async def exchange(self, code, flow):
        form = {
            **self.client_fields(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri,
        }
        if self.capability.pkce:
            form["code_verifier"] = flow.verifier
        result = await self.http.json("POST", self.token_endpoint, effect=True, data=form)
        tokens = self.token(result)
        if self.capability.oidc:
            tokens = await self.verify_tokens(tokens, flow.nonce, code=code)
        return tokens

    async def refresh(self, tokens):
        if not self.capability.refresh:
            raise AuthException(Codes.UNSUPPORTED)
        result = await self.http.json(
            "POST",
            self.refresh_endpoint or self.token_endpoint,
            effect=True,
            data={
                **self.client_fields(),
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_value(tokens),
            },
        )
        refreshed = self.token(result)
        if self.capability.oidc and refreshed.id_token is not None:
            if tokens.subject is None:
                raise AuthException(Codes.INPUT, outcome="unknown")
            refreshed = await self.verify_tokens(refreshed, tokens.nonce, previous=tokens)
        updates = {"nonce": tokens.nonce}
        if refreshed.claims is None:
            updates["claims"] = tokens.claims
        return refreshed.model_copy(update=updates)

    async def verify_tokens(self, tokens, nonce, *, code=None, previous=None):
        if tokens.id_token is None:
            raise AuthException(Codes.OIDC, outcome="unknown")
        try:
            claims = await self.oidc.verify(
                tokens.id_token.get_secret_value(),
                self.oidc_metadata,
                self.config.client_id,
                nonce,
                access_token=self.access(tokens),
                code=code,
                expected_subject=None if previous is None else previous.subject,
                previous_claims=None if previous is None else previous.claims,
            )
        except AuthException as error:
            # 已取得令牌响应，后续密钥/声明校验失败不能被解释成授权码尚未发送。
            raise AuthException(error.error_code, outcome="unknown", cause=error) from error
        return tokens.model_copy(
            update={
                "claims": claims,
                "subject": claims["sub"],
                "subject_type": "sub",
                "nonce": nonce,
            }
        )

    async def userinfo(self, tokens):
        data = await self.http.json(
            "GET",
            self.userinfo_endpoint,
            headers={"Authorization": "Bearer " + self.access(tokens)},
        )
        Payload.reject_errors(data)
        subject = Payload.identifier(data, self.subject_field)
        if tokens.subject is not None and subject != tokens.subject:
            raise AuthException(Codes.BINDING)
        return self.identity(data, subject)
