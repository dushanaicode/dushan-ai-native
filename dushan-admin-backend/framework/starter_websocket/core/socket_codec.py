import hashlib
import hmac
import json
import time

from pydantic import ValidationError

from framework.starter_websocket.definitions.constants.websocket_error_codes import (
    WebSocketErrorCodes,
)
from framework.starter_websocket.exception.websocket_exception import WebSocketException
from framework.starter_websocket.model.client_message import ClientMessage
from framework.starter_websocket.model.socket_delivery import SocketDelivery


class SocketCodec:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def _reject_constant(value):
        raise ValueError("非有限 JSON 数值")

    def parse(self, text):
        if len(text.encode()) > self.settings.max_message_bytes:
            raise WebSocketException(WebSocketErrorCodes.TOO_LARGE)
        try:
            value = json.loads(text, parse_constant=self._reject_constant)
            return ClientMessage.model_validate(value, strict=True, by_alias=True, by_name=False)
        except (ValueError, ValidationError) as error:
            raise WebSocketException(WebSocketErrorCodes.PROTOCOL, cause=error) from error

    def encode(self, message):
        body = message.model_dump_json(by_alias=True, exclude_none=True)
        if len(body.encode()) > self.settings.max_message_bytes:
            raise WebSocketException(WebSocketErrorCodes.TOO_LARGE)
        return body

    def _signature(self, envelope):
        body = json.dumps(
            envelope.model_dump(mode="json", exclude={"signature"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        return hmac.new(
            self.settings.signing_secret.get_secret_value().encode(), body, hashlib.sha256
        ).hexdigest()

    def sign(self, envelope):
        return envelope.model_copy(update={"signature": self._signature(envelope)})

    def decode_delivery(self, body):
        if len(body.encode()) > self.settings.max_message_bytes * 2 + 4096:
            raise WebSocketException(WebSocketErrorCodes.TOO_LARGE)
        try:
            envelope = SocketDelivery.model_validate_json(body)
        except ValidationError as error:
            raise WebSocketException(WebSocketErrorCodes.PROTOCOL, cause=error) from error
        if not hmac.compare_digest(envelope.signature, self._signature(envelope)):
            raise WebSocketException(WebSocketErrorCodes.AUTHENTICATION)
        if abs(time.time() - envelope.issued_at) > self.settings.envelope_max_age_seconds:
            raise WebSocketException(WebSocketErrorCodes.AUTHENTICATION)
        if envelope.action == "deliver":
            valid = (
                envelope.target is not None
                and envelope.message is not None
                and envelope.family_id is None
                and envelope.tenant_id is None
            )
        else:
            valid = (
                envelope.target is None
                and envelope.message is None
                and ((envelope.family_id is None) != (envelope.tenant_id is None))
            )
        if not valid:
            raise WebSocketException(WebSocketErrorCodes.PROTOCOL)
        if envelope.message is not None:
            self.encode(envelope.message)
        return envelope
