import base64
import binascii
import hashlib
import hmac
import json
import time

from pydantic import ValidationError

from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.message_envelope import MessageEnvelope


class MessageCodec:
    """规范 JSON + HMAC；签名验证早于身份恢复和业务模型反序列化。"""

    def __init__(self, settings):
        self.settings = settings
        self.secret = settings.signing_secret.get_secret_value().encode()

    @staticmethod
    def canonical(values) -> bytes:
        return json.dumps(
            values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()

    def sign(self, envelope: MessageEnvelope) -> MessageEnvelope:
        payload = self.canonical(envelope.model_dump(exclude={"signature"}))
        signature = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        return envelope.model_copy(update={"signature": signature})

    def encode(self, envelope: MessageEnvelope) -> bytes:
        body = envelope.model_dump_json().encode()
        if len(body) > self.wire_limit:
            raise MQException("invalid")
        return body

    @property
    def wire_limit(self):
        return (self.settings.max_message_bytes + self.settings.max_proof_bytes) * 2 + 16384

    def decode(self, body: bytes, destination: str, *, check_age=True) -> MessageEnvelope:
        if len(body) > self.wire_limit:
            raise MQException("invalid")
        try:
            envelope = MessageEnvelope.model_validate_json(body, strict=True)
        except ValidationError as error:
            raise MQException("invalid", cause=error) from error
        expected = self.sign(envelope).signature
        if not hmac.compare_digest(expected, envelope.signature):
            raise MQException("authentication")
        self.validate(envelope, destination, check_age=check_age)
        return envelope

    def validate(self, envelope, destination, *, check_age=True):
        now = time.time()
        skew = self.settings.clock_skew_seconds
        if envelope.destination != destination or envelope.issued_at > now + skew:
            raise MQException("authentication")
        if not 0 < envelope.expires_at - envelope.issued_at <= self.settings.max_age_seconds:
            raise MQException("authentication")
        if envelope.ready_at < envelope.issued_at or envelope.ready_at > envelope.expires_at:
            raise MQException("invalid")
        if envelope.authority == "session" and (
            envelope.capability is not None or envelope.tenant_id is None
        ):
            raise MQException("authentication")
        if envelope.authority == "workload" and not envelope.capability:
            raise MQException("authentication")
        if set(envelope.trace_headers) - {"traceparent", "tracestate"} or any(
            len(v) > 1024 for v in envelope.trace_headers.values()
        ):
            raise MQException("invalid")
        self.payload(envelope)
        self.proof(envelope)
        if check_age and envelope.expires_at < now - skew:
            raise MQException("expired")

    def payload(self, envelope) -> bytes:
        return self._bytes(envelope.payload, self.settings.max_message_bytes)

    def proof(self, envelope) -> bytes:
        return self._bytes(envelope.proof, self.settings.max_proof_bytes)

    @staticmethod
    def _bytes(value, limit):
        try:
            result = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as error:
            raise MQException("invalid", cause=error) from error
        if not 1 <= len(result) <= limit:
            raise MQException("invalid")
        return result

    @staticmethod
    def digest(envelope):
        return hashlib.sha256(
            MessageCodec.canonical(
                envelope.model_dump(exclude={"signature", "attempt", "ready_at", "consumer_key"})
            )
        ).hexdigest()

    def retry(self, envelope, key, delay):
        now = time.time()
        ready = now + delay
        if ready >= envelope.expires_at:
            raise MQException("expired")
        return self.sign(
            envelope.model_copy(
                update={"attempt": envelope.attempt + 1, "consumer_key": key, "ready_at": ready}
            )
        )
