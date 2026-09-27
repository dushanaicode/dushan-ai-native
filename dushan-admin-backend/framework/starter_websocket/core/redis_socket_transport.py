import asyncio
from contextvars import Context

from loguru import logger

from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.exception.websocket_exception import WebSocketException


class RedisSocketTransport:
    """可恢复的可丢广播通道；认证后只入本地连接队列。"""

    def __init__(self, runtime, client, channel):
        self.runtime, self.client, self.channel = runtime, client, channel
        self.subscription = None
        self.task = None
        self.running = False
        self.connected = False
        self.reconnects = 0

    @property
    def is_ready(self) -> bool:
        return self.running and self.connected and self.task is not None and not self.task.done()

    async def _subscribe(self):
        subscription = self.client.pubsub(ignore_subscribe_messages=False)
        self.subscription = subscription
        await subscription.subscribe(self.channel)
        confirmation = await subscription.get_message(
            timeout=self.runtime.settings.command_timeout_seconds
        )
        if confirmation is None or confirmation["type"] != "subscribe":
            raise WebSocketException(WebSocketErrorCodes.TRANSPORT)
        subscription.ignore_subscribe_messages = True
        self.connected = True

    async def open(self):
        await self.runtime.call(self._subscribe())
        self.running = True
        self.task = asyncio.create_task(self._run(), context=Context(), name="websocket-redis")

    async def _run(self):
        while self.running:
            try:
                while self.running:
                    item = await self.subscription.get_message(
                        timeout=self.runtime.settings.transport_poll_seconds
                    )
                    if item is not None:
                        try:
                            envelope = self.runtime.codec.decode_delivery(item["data"])
                        except WebSocketException:
                            self.runtime.rejected_envelopes += 1
                            continue
                        try:
                            self.runtime.receive_delivery(envelope)
                        except Exception as error:
                            self.runtime.record_error(error)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.connected = False
                self.runtime.record_error(error)
                logger.warning("WebSocket Redis 订阅中断 error_type={}", type(error).__name__)
            finally:
                self.connected = False
                await self._close_subscription()
            while self.running:
                await asyncio.sleep(self.runtime.settings.transport_restart_seconds)
                try:
                    await self.runtime.call(self._subscribe())
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    self.runtime.record_error(error)
                    await self._close_subscription()
                else:
                    self.reconnects += 1
                    break

    async def _close_subscription(self):
        if self.subscription is not None:
            try:
                await self.runtime.call(self.subscription.aclose())
            except Exception as error:
                self.runtime.record_error(error)
            finally:
                self.subscription = None

    async def publish(self, envelope):
        return await self.runtime.call(
            self.client.publish(self.channel, self.runtime.codec.sign(envelope).model_dump_json())
        )

    async def close(self):
        self.running = self.connected = False
        errors = []
        if self.task is not None:
            self.task.cancel()
            results = await asyncio.gather(self.task, return_exceptions=True)
            errors.extend(error for error in results if isinstance(error, Exception))
        if self.subscription is not None:
            try:
                await self.runtime.call(self.subscription.aclose())
            except Exception as error:
                errors.append(error)
            finally:
                self.subscription = None
        if errors:
            raise ExceptionGroup("WebSocket Redis 订阅关闭失败", errors)
