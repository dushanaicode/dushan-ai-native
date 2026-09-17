import asyncio
import hashlib
import time
from collections import Counter, deque
from contextvars import Context
from uuid import uuid4

from loguru import logger
from redis.asyncio.cluster import RedisCluster

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from framework.starter_websocket.core.online_registry import OnlineRegistry
from framework.starter_websocket.core.redis_socket_transport import RedisSocketTransport
from framework.starter_websocket.core.socket_authenticator import SocketAuthenticator
from framework.starter_websocket.core.socket_codec import SocketCodec
from framework.starter_websocket.core.socket_connection import SocketConnection
from framework.starter_websocket.enums.socket_transport import SocketTransport
from framework.starter_websocket.exception.socket_exception import SocketException
from framework.starter_websocket.model.socket_message import SocketMessage


class WebSocketRuntime:
    """应用拥有连接、心跳和 transport；所有长连接在 DI drain 前退出。"""

    def __init__(
        self,
        settings,
        application,
        registry,
        security,
        cache,
        tickets,
        monitor,
        translator,
        trusted_proxies,
        logging_owner,
        listener,
    ):
        self.settings, self.application, self.registry, self.security = (
            settings,
            application,
            registry,
            security,
        )
        self.monitor, self.translator, self.logging_owner, self.listeners = (
            monitor,
            translator,
            logging_owner,
            listener,
        )
        self.instance = uuid4().hex
        self.codec = SocketCodec(settings)
        self.authenticator = SocketAuthenticator(self, tickets, trusted_proxies)
        self.connections = {}
        self.member_counts, self.tenant_counts = Counter(), Counter()
        self.errors = deque(maxlen=64)
        self.handled = self.slow_connections = self.rejected_envelopes = self.listener_failures = 0
        self.peak_inbound = self.peak_outbound = 0
        self.phase = "new"
        self.transport = self.online = None
        self._heartbeat = self._lease = self._quiesce_task = self._close_task = None
        self.handshakes = set()
        if settings.transport is SocketTransport.REDIS:
            if cache is None:
                raise SocketException("configuration")
            client = cache.get_client(settings.cache_key())
            if isinstance(client, RedisCluster):
                raise SocketException("configuration")
            application_key = hashlib.sha256(security.settings.application_id.encode()).hexdigest()[
                :16
            ]
            prefix = cache.build_full_key(
                settings.cache_key(), settings.namespace + ":" + application_key
            )
            self.online = OnlineRegistry(self, client, prefix)
            self.transport = RedisSocketTransport(self, client, prefix + ":broadcast")

    @property
    def accepting(self):
        return self.phase == "ready" and (self.online is None or self.online.valid)

    async def call(self, awaitable):
        async with asyncio.timeout(self.settings.command_timeout_seconds):
            return await awaitable

    async def open(self):
        self.phase = "starting"
        logger.info(
            "【WebSocketStarter 】开始初始化 WebSocket 运行时：{}", self.settings.transport.value
        )
        if self.online is not None:
            await self.call(self.online.open())
            await self.transport.open()
            self._lease = asyncio.create_task(
                self._renew(), context=Context(), name="websocket-instance"
            )
            logger.info("【WebSocketStarter 】Redis 在线注册、广播传输与实例续租已启动")
        else:
            logger.info("【WebSocketStarter 】已选择进程内消息传输")
        self._heartbeat = asyncio.create_task(
            self._heartbeats(), context=Context(), name="websocket-heartbeats"
        )
        self.phase = "ready"
        logger.info("【WebSocketStarter 】运行时初始化完成，连接心跳任务已登记")

    async def authorize(self, websocket, endpoint):
        task = asyncio.current_task()
        self.handshakes.add(task)
        try:
            handshake = await self.authenticator.authenticate(websocket)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.record_error(error)
            # accept 前 close 按 ASGI 转换为拒绝握手，不伪造已建立连接的错误帧。
            code = 1013 if isinstance(error, TimeoutError) else 4001
            if isinstance(error, SocketException):
                code = {"policy": 4002, "protocol": 4002, "capacity": 1013, "closed": 1001}.get(
                    error.reason, 4001
                )
            await websocket.close(code)
            return
        finally:
            self.handshakes.discard(task)
        if not self.accepting:
            await websocket.close(1001)
            return
        await endpoint(websocket, handshake)

    @staticmethod
    def _member_key(connection):
        session = connection.session
        return (
            session.realm.value,
            session.authority_tenant_id,
            session.authority_membership_id,
            session.account_id,
        )

    async def serve(self, websocket, handshake):
        await websocket.accept(subprotocol=handshake.subprotocol)
        connection = SocketConnection(self, websocket, handshake)
        member = self._member_key(connection)
        tenant = connection.session.tenant_id
        if (
            not self.accepting
            or len(self.connections) >= self.settings.max_connections
            or self.member_counts[member] >= self.settings.max_connections_per_member
            or self.tenant_counts[tenant] >= self.settings.max_connections_per_tenant
        ):
            await websocket.close(4003)
            return
        self.connections[connection.id] = connection
        self.member_counts[member] += 1
        self.tenant_counts[tenant] += 1
        connection.created_at = time.time()
        connection.last_ping = time.monotonic()
        try:
            if self.online is not None:
                await self.call(self.online.add(connection.information))
            await self.notify("connected", connection.information)
            if connection._close_task is None:
                await connection.run()
        except asyncio.CancelledError:
            await AsyncioUtils.run_cancellation_shielded(
                connection.close(), propagate_cancellation=False
            )
            raise
        except Exception as error:
            self.record_error(error)
            await connection.close(1011)
        finally:
            await AsyncioUtils.run_cancellation_shielded(
                connection.close(), propagate_cancellation=False
            )

    async def remove(self, connection):
        if self.connections.get(connection.id) is not connection:
            return
        del self.connections[connection.id]
        member, tenant = self._member_key(connection), connection.session.tenant_id
        for counts, key in ((self.member_counts, member), (self.tenant_counts, tenant)):
            counts[key] -= 1
            if not counts[key]:
                del counts[key]
        self.peak_inbound = max(self.peak_inbound, connection.peak_inbound)
        self.peak_outbound = max(self.peak_outbound, connection.peak_outbound)
        try:
            if self.online is not None:
                await self.call(self.online.remove(connection.information))
        finally:
            await self.notify("disconnected", connection.information, connection.close_code)

    async def notify(self, method, *args):
        for listener in self.listeners:
            if listener.audience != args[0].audience:
                continue
            try:
                await self.call(
                    self.application.tasks.run_isolated(lambda: getattr(listener, method)(*args))
                )
            except Exception as error:
                self.listener_failures += 1
                self.record_error(error)

    @staticmethod
    def matches(information, target):
        return OnlineRegistry.matches(information, target)

    def receive_delivery(self, envelope):
        if not self.accepting:
            return 0
        selected = tuple(self.connections.values())
        if envelope.action == "invalidate":
            total = 0
            for connection in selected:
                if connection.created_at <= envelope.issued_at and (
                    envelope.family_id == connection.session.family_id
                    or envelope.tenant_id is not None
                    and envelope.tenant_id == connection.session.tenant_id
                ):
                    connection.request_close(4001)
                    total += 1
            return total
        target, message = envelope.target, envelope.message
        try:
            self.registry.event_payload(target.audience, message.type, message.payload)
        except SocketException:
            self.rejected_envelopes += 1
            return 0
        return sum(
            connection.enqueue(message)
            for connection in selected
            if self.matches(connection.information, target)
        )

    async def _heartbeats(self):
        await self.application.wait_until_ready()
        while self.phase == "ready":
            await asyncio.sleep(self.settings.authorization_refresh_seconds)
            connections = iter(tuple(self.connections.values()))

            async def worker():
                for connection in connections:
                    if connection.phase != "active":
                        continue
                    observed = connection.last_activity
                    if time.monotonic() - observed > self.settings.heartbeat_timeout_seconds:
                        if observed == connection.last_activity:
                            connection.request_close(1001)
                        continue
                    try:
                        await self.authenticator.refresh(connection)
                    except asyncio.CancelledError:
                        raise
                    except Exception as error:
                        connection.request_close(4001, error)
                        continue
                    now = time.monotonic()
                    if now - connection.last_ping >= self.settings.heartbeat_interval_seconds:
                        connection.last_ping = now
                        connection.enqueue(SocketMessage(type="ping"), builtin=True)

            tasks = [
                asyncio.create_task(worker(), context=Context())
                for _ in range(min(len(self.connections), self.settings.authorization_concurrency))
            ]
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _renew(self):
        while self.phase in {"starting", "ready"}:
            await asyncio.sleep(self.settings.instance_renew_seconds)
            try:
                await self.call(self.online.renew())
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.record_error(error)
                if not self.online.valid:
                    for connection in tuple(self.connections.values()):
                        connection.request_close(1013)
                    return

    def record_error(self, error):
        self.errors.append(error)
        logger.warning("WebSocket 操作异常 error_type={}", type(error).__name__)

    async def quiesce(self):
        if self._quiesce_task is None:
            self.phase = "draining"
            self._quiesce_task = asyncio.create_task(
                self._quiesce(), context=Context(), name="websocket-quiesce"
            )
        await asyncio.shield(self._quiesce_task)

    async def _quiesce(self):
        errors = []
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            await asyncio.gather(self._heartbeat, return_exceptions=True)
        if self.transport is not None:
            try:
                await self.transport.close()
            except Exception as error:
                errors.append(error)
        for task in tuple(self.handshakes):
            task.cancel()
        await asyncio.gather(*tuple(self.handshakes), return_exceptions=True)
        results = await asyncio.gather(
            *(connection.close() for connection in tuple(self.connections.values())),
            return_exceptions=True,
        )
        errors.extend(error for error in results if isinstance(error, Exception))
        if errors:
            raise ExceptionGroup("WebSocket 连接排空失败", errors)

    async def close(self):
        if self._close_task is None:
            self._close_task = asyncio.create_task(
                self._close(), context=Context(), name="websocket-close"
            )
        await asyncio.shield(self._close_task)

    async def _close(self):
        errors = []
        try:
            await self.quiesce()
        except Exception as error:
            errors.append(error)
        if self._lease is not None:
            self._lease.cancel()
            await asyncio.gather(self._lease, return_exceptions=True)
        if self.online is not None:
            try:
                await self.call(self.online.close())
            except Exception as error:
                errors.append(error)
        self.phase = "closed"
        if errors:
            raise ExceptionGroup("WebSocket 关闭失败", errors)

    def resources(self):
        return {
            "state": self.phase,
            "instance_id": self.instance,
            "connections": len(self.connections),
            "handshakes": self.authenticator.pending,
            "inbound": sum(connection.inbound.qsize() for connection in self.connections.values()),
            "outbound": sum(
                connection.outbound.qsize() for connection in self.connections.values()
            ),
            "peak_inbound": max(
                [
                    self.peak_inbound,
                    *(connection.peak_inbound for connection in self.connections.values()),
                ]
            ),
            "peak_outbound": max(
                [
                    self.peak_outbound,
                    *(connection.peak_outbound for connection in self.connections.values()),
                ]
            ),
            "active_handlers": sum(
                connection.active_handlers for connection in self.connections.values()
            ),
            "handled": self.handled,
            "slow_connections": self.slow_connections,
            "rejected_envelopes": self.rejected_envelopes,
            "listener_failures": self.listener_failures,
            "error_types": tuple(type(error).__name__ for error in self.errors),
            "subscription_connected": self.transport is not None and self.transport.connected,
            "subscription_reconnects": 0 if self.transport is None else self.transport.reconnects,
            "instance_lease_valid": self.online is not None and self.online.valid,
        }
