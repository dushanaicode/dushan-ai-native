from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from framework.starter_di.decorators.components import util
from framework.starter_security.core.opaque_token import OpaqueToken


@util
class OAuth2Utils:
    @staticmethod
    async def append_query_param(url: str, params: dict) -> str:
        parts = urlsplit(url)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in params
        ]
        return urlunsplit(parts._replace(query=urlencode(query + list(params.items()))))

    async def build_authorization_code_redirect_uri(
        self, redirect_uri, authorization_code, state=None
    ):
        params = {"code": authorization_code}
        if state is not None:
            params["state"] = state
        return await self.append_query_param(redirect_uri, params)

    async def build_implicit_redirect_uri(
        self, redirect_uri, access_token, state, expire_time, scopes, additional_information=None
    ):
        params = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.get_expires_in(expire_time),
            "scope": " ".join(scopes),
        }
        if state is not None:
            params["state"] = state
        if additional_information is not None:
            params["additional_information"] = additional_information
        return urlunsplit(urlsplit(redirect_uri)._replace(fragment=urlencode(params)))

    async def build_unsuccessful_redirect(
        self, redirect_uri, response_type, state, error, description
    ):
        params = {"error": error, "error_description": description}
        if state is not None:
            params["state"] = state
        if response_type == "token":
            return urlunsplit(urlsplit(redirect_uri)._replace(fragment=urlencode(params)))
        return await self.append_query_param(redirect_uri, params)

    @staticmethod
    async def build_scopes(scope: str | None) -> list[str]:
        return [] if scope is None else scope.split()

    @staticmethod
    async def build_scope_str(scopes: list[str]) -> str:
        return " ".join(scopes)

    @staticmethod
    def get_expires_in(expire_time: datetime) -> int:
        return max(
            0, int((expire_time - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())
        )

    @staticmethod
    def get_user_info(user) -> dict:
        return {} if user is None else {"nickname": user.nickname, "dept_id": user.dept_id}

    @staticmethod
    def calculate_ttl(expiry: datetime) -> int:
        return OAuth2Utils.get_expires_in(expiry)

    @staticmethod
    def convert_expiry_to_timestamp(expiry: datetime) -> int:
        return int(expiry.replace(tzinfo=timezone.utc).timestamp() * 1000)

    @staticmethod
    def build_token_payload(token_record) -> dict:
        return {
            "user_id": token_record.user_id,
            "user_type": token_record.user_type,
            "scopes": token_record.scopes,
            "client_id": token_record.client_id,
            "exp": int(token_record.expires_time.replace(tzinfo=timezone.utc).timestamp()),
        }

    @staticmethod
    def generate_token() -> str:
        return OpaqueToken.generate()

    @staticmethod
    def get_expiry(client, token_type: str) -> datetime:
        seconds = {
            "access": client.access_token_validity_seconds,
            "refresh": client.refresh_token_validity_seconds,
        }[token_type]
        return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=seconds)
