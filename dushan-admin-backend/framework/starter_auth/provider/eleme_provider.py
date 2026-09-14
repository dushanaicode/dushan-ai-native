import hashlib
import json
import time
from uuid import uuid4

import httpx

from framework.starter_auth.model.provider_capability import ProviderCapability
from framework.starter_auth.provider.oauth_provider import OAuthProvider
from framework.starter_auth.provider.provider_payload import ProviderPayload as Payload


class ElemeProvider(OAuthProvider):
    subject_field = "userId"
    capabilities = (ProviderCapability("ELEME", refresh=True),)
    authorization_endpoint = "https://open-api.shop.ele.me/authorize"
    token_endpoint = "https://open-api.shop.ele.me/token"
    userinfo_endpoint = "https://open-api.shop.ele.me/api/v1/"
    fixed_scopes = ()
    profile_fields = {"username": "userName", "nickname": "userName"}

    async def _token(self, params):
        data = await self.http.json(
            "POST",
            self.token_endpoint,
            effect=True,
            data=params,
            auth=httpx.BasicAuth(
                self.config.client_id, self.config.client_secret.get_secret_value()
            ),
        )
        return self.token(data)

    async def exchange(self, code, flow):
        return await self._token(
            {
                "client_id": self.config.client_id,
                "redirect_uri": self.config.redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            }
        )

    async def refresh(self, tokens):
        return await self._token(
            {"grant_type": "refresh_token", "refresh_token": self.refresh_value(tokens)}
        )

    @staticmethod
    def signature(secret, action, token, metadata, params):
        combined = {**params, **metadata}
        values = "".join(
            f"{key}={json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
            for key, value in sorted(combined.items())
        )
        return hashlib.md5((action + token + values + secret).encode()).hexdigest().upper()

    async def userinfo(self, tokens):
        action, access = "eleme.user.getUser", self.access(tokens)
        metadata = {"app_key": self.config.client_id, "timestamp": int(time.time())}
        data = await self.http.json(
            "POST",
            self.userinfo_endpoint,
            json={
                "nop": "1.0.0",
                "id": uuid4().hex,
                "action": action,
                "token": access,
                "metas": metadata,
                "params": {},
                "signature": self.signature(
                    self.config.client_secret.get_secret_value(), action, access, metadata, {}
                ),
            },
        )
        Payload.reject_errors(data)
        profile = Payload.object(data, "result")
        return self.identity(profile, Payload.identifier(profile, "userId"))
