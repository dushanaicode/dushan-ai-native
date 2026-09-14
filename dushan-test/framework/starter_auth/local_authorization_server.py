import asyncio
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from joserfc import jwt

from .support import SECRET, rsa_key


class LocalAuthorizationServer:
    """实际 TCP HTTP 授权服务；校验 code、回调、PKCE，并签发可轮换的 RSA ID Token。"""

    def __init__(self):
        self.key = rsa_key()
        self.codes = {}
        self.refresh_tokens = {}
        self.access_tokens = set()
        self.calls = []
        self._tasks = set()
        self.release_slow = asyncio.Event()
        self.started_slow = asyncio.Event()
        self.closed = False
        self.nonce_override = None
        self.client_secret = SECRET

    async def open(self):
        self.server = await asyncio.start_server(self._connection, "127.0.0.1", 0)
        self.origin = "http://127.0.0.1:" + str(self.server.sockets[0].getsockname()[1])
        return self

    async def _connection(self, reader, writer):
        self._tasks.add(asyncio.current_task())
        try:
            while True:
                try:
                    raw = await reader.readuntil(b"\r\n\r\n")
                except asyncio.IncompleteReadError:
                    break
                lines = raw.decode().split("\r\n")
                method, target, _ = lines[0].split(" ", 2)
                headers = {
                    name.lower(): value
                    for line in lines[1:]
                    if line
                    for name, value in (line.split(": ", 1),)
                }
                body = await reader.readexactly(int(headers.get("content-length", "0")))
                status, content, extra = await self.dispatch(method, target, body, headers)
                if isinstance(content, dict):
                    content = json.dumps(content).encode()
                response = (
                    f"HTTP/1.1 {status} Test\r\nContent-Length: {len(content)}\r\nContent-Type: application/json\r\n{extra}\r\n".encode()
                    + content
                )
                writer.write(response)
                await writer.drain()
        except (ConnectionError, BrokenPipeError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass
            finally:
                self._tasks.remove(asyncio.current_task())

    async def dispatch(self, method, target, body, headers):
        path = urlsplit(target).path
        query = {k: v[0] for k, v in parse_qs(urlsplit(target).query).items()}
        form = {k: v[0] for k, v in parse_qs(body.decode()).items()}
        self.calls.append((method, path))
        if path == "/authorize":
            if query.get("code_challenge_method") != "S256":
                return 400, {"error": "invalid_pkce"}, ""
            code = secrets.token_urlsafe(24)
            self.codes[code] = query
            redirect = (
                query["redirect_uri"] + "?" + urlencode({"state": query["state"], "code": code})
            )
            return 302, b"", "Location: " + redirect + "\r\n"
        if path == "/.well-known/openid-configuration":
            return (
                200,
                {
                    "issuer": self.origin,
                    "jwks_uri": self.origin + "/keys",
                    "authorization_endpoint": self.origin + "/authorize",
                    "token_endpoint": self.origin + "/token",
                    "id_token_signing_alg_values_supported": ["RS256"],
                },
                "",
            )
        if path == "/keys":
            return 200, {"keys": [self.key.as_dict(private=False)]}, ""
        if path == "/token":
            if (
                form.get("client_id") != "client-a"
                or form.get("client_secret") != self.client_secret
            ):
                return 400, {"error": "invalid_client"}, ""
            refresh = form.get("grant_type") == "refresh_token"
            if refresh:
                saved = self.refresh_tokens.pop(form.get("refresh_token"), None)
            else:
                saved = self.codes.pop(form.get("code"), None)
            if saved is None:
                return 400, {"error": "invalid_grant"}, ""
            if not refresh:
                challenge = (
                    base64.urlsafe_b64encode(
                        hashlib.sha256(form.get("code_verifier", "").encode()).digest()
                    )
                    .rstrip(b"=")
                    .decode()
                )
                if (
                    challenge != saved["code_challenge"]
                    or form.get("redirect_uri") != saved["redirect_uri"]
                ):
                    return 400, {"error": "invalid_grant"}, ""
            access, fresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            self.access_tokens.add(access)
            self.refresh_tokens[fresh] = saved
            claims = {
                "iss": self.origin,
                "aud": "client-a",
                "sub": "local-subject",
                "iat": int(time.time()),
                "exp": int(time.time()) + 600,
            }
            if not refresh:
                claims["nonce"] = self.nonce_override or saved["nonce"]
            encoded = jwt.encode({"alg": "RS256", "kid": self.key.kid}, claims, self.key)
            return (
                200,
                {
                    "access_token": access,
                    "refresh_token": fresh,
                    "id_token": encoded,
                    "expires_in": 600,
                    "token_type": "Bearer",
                },
                "",
            )
        if path == "/user":
            access = headers.get("authorization", "").removeprefix("Bearer ")
            # header 字段名忽略大小写，令牌值不做大小写归一。
            if access not in self.access_tokens:
                return 401, {"error": "invalid_token"}, ""
            return 200, {"sub": "local-subject", "name": "Local User"}, ""
        if path == "/revoke":
            self.access_tokens.discard(form.get("token"))
            return 200, {}, ""
        if path == "/slow":
            self.started_slow.set()
            await self.release_slow.wait()
            return 200, {}, ""
        if path == "/oversize":
            return 200, b"x" * 8192, ""
        return 404, {}, ""

    async def close(self):
        self.release_slow.set()
        self.server.close()
        await self.server.wait_closed()
        for task in tuple(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self.closed = True
