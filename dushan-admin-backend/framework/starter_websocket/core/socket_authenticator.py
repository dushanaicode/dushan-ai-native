import asyncio
import re
import time
from urllib.parse import parse_qsl

from starlette.datastructures import Headers

from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.model.socket_handshake import SocketHandshake


class SocketAuthenticator:
    """只消费一次性票据；清除 scope 中的凭证后才 accept/拒绝，避免协议日志泄漏。"""

    _FORBIDDEN = frozenset(
        {
            "authorization",
            "token",
            "accesstoken",
            "xtoken",
            "xaccesstoken",
            "tenantid",
            "activetenantid",
            "sourcetenantid",
            "visittenantid",
            "xtenantid",
            "xactivetenantid",
            "xsourcetenantid",
            "xvisittenantid",
        }
    )

    def __init__(self, runtime, tickets, trusted_proxies):
        self.runtime, self.tickets, self.trusted_proxies = runtime, tickets, trusted_proxies
        self.pending = 0

    async def authenticate(self, websocket):
        runtime = self.runtime
        raw_query = websocket.scope["query_string"]
        websocket.scope["query_string"] = b""
        original_headers = websocket.scope["headers"]
        websocket.scope["headers"] = [
            (key, value)
            for key, value in original_headers
            if key.lower() not in {b"cookie", b"authorization", b"sec-websocket-protocol"}
        ]
        if not runtime.accepting:
            raise SocketException("closed")
        if self.pending >= runtime.settings.max_pending_handshakes:
            raise SocketException("capacity")
        self.pending += 1
        try:
            async with asyncio.timeout(runtime.settings.handshake_timeout_seconds):
                headers = Headers(raw=original_headers)
                if any(
                    key.lower().replace("-", "").replace("_", "") in self._FORBIDDEN
                    for key in headers
                ):
                    raise SocketException("policy")
                try:
                    pairs = parse_qsl(
                        raw_query.decode("ascii"),
                        keep_blank_values=True,
                        strict_parsing=True,
                        max_num_fields=4,
                    )
                except (ValueError, UnicodeError) as error:
                    raise SocketException("protocol", cause=error) from error
                params = dict(pairs)
                if len(pairs) != len(params) or set(params) != {"ticket", "audience"}:
                    raise SocketException("policy")
                if re.fullmatch(r"[A-Za-z0-9_-]{16,512}", params["ticket"]) is None:
                    raise SocketException("authentication")
                origin = headers.getlist("origin")
                if len(origin) != 1 or origin[0] not in runtime.settings.allowed_origins:
                    raise SocketException("policy")
                requested = websocket.scope["subprotocols"]
                if any(value not in runtime.settings.subprotocols for value in requested):
                    raise SocketException("policy")
                protocol = next(
                    (value for value in runtime.settings.subprotocols if value in requested), None
                )
                audience = runtime.registry.audience(params["audience"])
                peer = websocket.scope["client"]
                client_ip = ClientIpResolver.resolve_client_ip(
                    headers, None if peer is None else peer[0], self.trusted_proxies
                )
                started = time.monotonic()

                async def resolve(*, application_id, domain):
                    return await self.tickets.consume(
                        params["ticket"], application_id=application_id, domain=domain
                    )

                async def authorized(session):
                    allowed = await runtime.security.allowed_policies(
                        runtime.registry.policies(audience.key)
                    )
                    return SocketHandshake(
                        session,
                        audience.key,
                        allowed,
                        started,
                        client_ip,
                        headers.get("accept-language"),
                        protocol,
                    )

                return await runtime.security.run_authenticated(
                    resolve, audience.policy, authorized
                )
        finally:
            self.pending -= 1

    async def refresh(self, connection):
        runtime = self.runtime
        started = time.monotonic()

        async def current(session):
            allowed = await runtime.security.allowed_policies(
                runtime.registry.policies(connection.audience)
            )
            return session, allowed

        async with asyncio.timeout(runtime.settings.authorization_timeout_seconds):
            session, allowed = await runtime.security.run_session_reference(
                connection.session, runtime.registry.audience(connection.audience).policy, current
            )
        connection.session = session
        connection.allowed_events = allowed
        connection.validated_at = started
