import json
import time
from urllib.parse import parse_qs

import httpx
from joserfc import jwt
from joserfc.jwk import RSAKey

from fixtures.config_factory import ConfigFactory
from framework.starter_auth.config.auth_client_config import AuthClientConfig
from framework.starter_auth.config.auth_settings import AuthSettings
from framework.starter_auth.core.auth_http_client import AuthHttpClient
from framework.starter_auth.core.auth_provider_registry import AuthProviderRegistry
from framework.starter_auth.model.auth_flow import AuthFlow
from framework.starter_auth.oidc.oidc_verifier import OidcVerifier

SECRET = "test-client-secret-do-not-log"
ACCESS = "test-access-secret-do-not-log"
REFRESH = "test-refresh-secret-do-not-log"
BINDING = "browser-session-binding-" + "x" * 32


def client_config(source="GITHUB", application_id="app-a", **changes):
    registry = AuthProviderRegistry()
    capability = registry.capability(source)
    cls = registry.get(source)
    scopes = cls.fixed_scopes if cls.fixed_scopes is not None else ()
    if source in ("HUAWEI_V3", "ALIYUN"):
        scopes = ("openid",)
    if source in ("WECHAT_MP", "WECHAT_ENTERPRISE_WEB"):
        scopes = ("snsapi_base",)
    if source == "WECHAT_OPEN":
        scopes = ("snsapi_login",)
    if source == "DINGTALK_V2":
        scopes = ("openid",)
    options = {"agent_id": "12345", "lang": "en"} if source.startswith("WECHAT_ENTERPRISE") else {}
    values = dict(
        application_id=application_id,
        source=source,
        enabled=True,
        revision=1,
        client_id="client-a",
        client_secret=SECRET,
        redirect_uri=None
        if capability.mode == "native"
        else "https://app.example/callback?purpose=bind",
        scopes=scopes,
        pkce=capability.pkce,
        options=options,
        credentials={},
    )
    values.update(changes)
    return AuthClientConfig(**values)


def settings(**changes):
    values = ConfigFactory.values()["config"]["models"]["auth"]
    values.update(enabled=True, namespace="auth-tests", allow_loopback_http=True)
    values.update(changes)
    return AuthSettings(**values)


def rsa_key(kid="key-one"):
    return RSAKey.generate_key(2048, parameters={"kid": kid, "use": "sig"})


class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.closed = False

    async def handle_async_request(self, request):
        self.requests.append(request)
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        if callable(result):
            result = result(request)
        if isinstance(result, httpx.Response):
            return result
        if isinstance(result, (bytes, str)):
            return httpx.Response(200, content=result)
        return httpx.Response(200, json=result)

    async def aclose(self):
        self.closed = True


class Credentials:
    def __init__(self):
        self.calls = 0

    async def get_or_load(self, config, loader):
        self.calls += 1
        return (await loader())[0]


def body(request):
    if request.headers.get("content-type", "").startswith("application/json"):
        return json.loads(request.content)
    return {k: v[0] for k, v in parse_qs(request.content.decode(), keep_blank_values=True).items()}


async def provider_case(source, responses, config=None):
    cfg = config or client_config(source)
    transport = RecordingTransport(responses)
    http = AuthHttpClient(settings(), transport=transport)
    provider = AuthProviderRegistry().get(source)(
        cfg, http, Credentials(), OidcVerifier(http, settings())
    )
    return provider, transport, http


def oidc_token(key, metadata, initial_nonce, **changes):
    claims = {
        "iss": metadata.issuer,
        "aud": "client-a",
        "sub": "external-subject",
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "nonce": initial_nonce,
        "name": "External user",
        "email": "user@example.test",
        "email_verified": True,
    }
    claims.update(changes)
    return jwt.encode({"alg": "RS256", "kid": key.kid}, claims, key)


FLOW = AuthFlow(state="s" * 43, verifier="v" * 64, nonce="n" * 43)

# 独立协议样例，不从生产代码生成字段映射。
TOKEN = {
    "access_token": ACCESS,
    "refresh_token": REFRESH,
    "expires_in": 600,
    "token_type": "Bearer",
}
CHANNEL_RESPONSES = {
    "GITHUB": [TOKEN, {"id": 123, "login": "octo", "name": "Octo"}],
    "GITEE": [TOKEN, {"id": 123, "login": "git-user"}],
    "BAIDU": [TOKEN, {"openid": "123", "username": "baidu-user", "sex": "1", "portrait": "photo"}],
    "CSDN": [TOKEN, {"username": "csdn-user", "description": "bio"}],
    "HUAWEI": [TOKEN, {"userID": "123", "userName": "hw", "gender": 0}],
    "QQ": [
        f"access_token={ACCESS}&expires_in=600&refresh_token={REFRESH}",
        'callback( {"client_id":"client-a","openid":"123","unionid":"union"} );',
        {"ret": 0, "nickname": "qq", "gender": "女", "figureurl_qq_2": "https://avatar.example/a"},
    ],
    "WECHAT_OPEN": [
        {**TOKEN, "openid": "123", "scope": "snsapi_login"},
        {"openid": "123", "unionid": "union", "nickname": "wx", "sex": 1},
    ],
    "WECHAT_MP": [{**TOKEN, "openid": "123", "scope": "snsapi_base", "is_snapshotuser": 1}],
    "WECHAT_MINI_PROGRAM": [
        {"openid": "123", "unionid": "union", "session_key": "session-key-secret"}
    ],
    "QQ_MINI_PROGRAM": [{"openid": "123", "session_key": "session-key-secret"}],
    "WECHAT_ENTERPRISE": [
        {"access_token": ACCESS, "expires_in": 7200},
        {"UserId": "123"},
        {"userid": "123", "name": "employee"},
    ],
    "WECHAT_ENTERPRISE_WEB": [
        {"access_token": ACCESS, "expires_in": 7200},
        {"UserId": "123"},
        {"userid": "123", "name": "employee"},
    ],
    "WECHAT_ENTERPRISE_CORP_APP": [{"access_token": ACCESS, "expires_in": 7200}, {"userid": "123"}],
    "DINGTALK": [
        {"errcode": 0, "user_info": {"openid": "123", "unionid": "union", "nick": "ding"}}
    ],
    "DINGTALK_ACCOUNT": [
        {"errcode": 0, "user_info": {"openid": "123", "unionid": "union", "nick": "ding"}}
    ],
    "DINGTALK_V2": [
        {"accessToken": ACCESS, "refreshToken": REFRESH, "expireIn": 600},
        {"openId": "123", "unionId": "union", "nick": "ding-v2", "visitor": True},
    ],
    "FEISHU": [
        {"code": 0, **TOKEN, "refresh_token_expires_in": 3600},
        {"code": 0, "data": {"open_id": "123", "union_id": "union", "name": "feishu"}},
    ],
    "DOUYIN": [
        {"data": {**TOKEN, "open_id": "123", "error_code": "0", "refresh_expires_in": 3600}},
        {
            "data": {
                "error_code": 0,
                "open_id": "123",
                "union_id": "union",
                "nickname": "dy",
                "gender": 2,
            }
        },
    ],
    "TOUTIAO": [{**TOKEN, "open_id": "123"}, {"data": {"uid": "123", "uid_type": 14}}],
    "TAOBAO": [{**TOKEN, "taobao_open_uid": "123", "taobao_user_nick": "%E6%B8%A1%E5%B1%B1"}],
    "WEIBO": [{**TOKEN, "uid": "123"}, {"idstr": "123", "screen_name": "wb", "gender": "f"}],
    "MEITUAN": [TOKEN, {"openid": "123", "nickname": "mt"}],
    "MI": [
        "&&&START&&&" + json.dumps({**TOKEN, "openId": "123"}),
        {"result": "ok", "data": {"miliaoNick": "mi"}},
    ],
    "JD": [
        {**TOKEN, "open_id": "123"},
        {
            "jingdong_user_getUserInfoByOpenId_response": {
                "getuserinfobyappidandopenid_result": {"data": {"nickName": "jd"}}
            }
        },
    ],
    "ELEME": [TOKEN, {"result": {"userId": "123", "userName": "shop"}}],
}

EXPECTED_TOKEN_REQUEST = {
    "GITHUB": ("POST", "github.com", "/login/oauth/access_token", "body", "client_id", "code"),
    "GITEE": ("POST", "gitee.com", "/oauth/token", "body", "client_id", "code"),
    "BAIDU": ("POST", "openapi.baidu.com", "/oauth/2.0/token", "body", "client_id", "code"),
    "CSDN": ("POST", "api.csdn.net", "/oauth2/access_token", "query", "client_id", "code"),
    "HUAWEI": (
        "POST",
        "oauth-login.cloud.huawei.com",
        "/oauth2/v2/token",
        "body",
        "client_id",
        "code",
    ),
    "QQ": ("GET", "graph.qq.com", "/oauth2.0/token", "query", "client_id", "code"),
    "WECHAT_OPEN": (
        "GET",
        "api.weixin.qq.com",
        "/sns/oauth2/access_token",
        "query",
        "appid",
        "code",
    ),
    "WECHAT_MP": ("GET", "api.weixin.qq.com", "/sns/oauth2/access_token", "query", "appid", "code"),
    "WECHAT_MINI_PROGRAM": (
        "GET",
        "api.weixin.qq.com",
        "/sns/jscode2session",
        "query",
        "appid",
        "js_code",
    ),
    "QQ_MINI_PROGRAM": ("GET", "api.q.qq.com", "/sns/jscode2session", "query", "appid", "js_code"),
    "DINGTALK_V2": (
        "POST",
        "api.dingtalk.com",
        "/v1.0/oauth2/userAccessToken",
        "body",
        "clientId",
        "code",
    ),
    "FEISHU": ("POST", "accounts.feishu.cn", "/oauth/v3/token", "body", "client_id", "code"),
    "DOUYIN": ("POST", "open.douyin.com", "/oauth/access_token/", "body", "client_key", "code"),
    "TOUTIAO": ("GET", "open.snssdk.com", "/auth/token", "query", "client_key", "code"),
    "TAOBAO": ("POST", "oauth.taobao.com", "/token", "body", "client_id", "code"),
    "WEIBO": ("POST", "api.weibo.com", "/oauth2/access_token", "body", "client_id", "code"),
    "MEITUAN": (
        "POST",
        "openapi.waimai.meituan.com",
        "/oauth/access_token",
        "body",
        "app_id",
        "code",
    ),
    "MI": ("GET", "account.xiaomi.com", "/oauth2/token", "query", "client_id", "code"),
    "JD": ("POST", "open-oauth.jd.com", "/oauth2/access_token", "body", "app_key", "code"),
    "ELEME": ("POST", "open-api.shop.ele.me", "/token", "body", "client_id", "code"),
}
