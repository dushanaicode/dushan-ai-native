import inspect
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from enum import Enum
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from framework.starter_protection.core.protection_key import ProtectionKey
from framework.starter_protection.web.distributed_lock import distributed_lock
from framework.starter_protection.web.idempotent import idempotent
from framework.starter_protection.web.rate_limit import rate_limit


class Payload(BaseModel):
    password: SecretStr
    amount: Decimal


class Named(Enum):
    ONE = "one"


class ExtraPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: int


def test_validated_extra_fields_participate_in_key(subject):
    first = ExtraPayload(value=1, business_extra="one")
    second = ExtraPayload(value=1, business_extra="two")
    assert ProtectionKey.build("extra", subject, first, 65536) != ProtectionKey.build(
        "extra", subject, second, 65536
    )


@pytest.mark.parametrize(
    "left,right",
    [
        (1, "1"),
        (True, 1),
        (1.0, 1),
        ([1], (1,)),
        ({1}, frozenset({1})),
        (Named.ONE, "one"),
        (SecretStr("a"), SecretStr("b")),
        (Payload(password="a", amount=1), Payload(password="b", amount=1)),
    ],
)
def test_canonical_types_and_secrets_do_not_collide(subject, left, right):
    assert ProtectionKey.build("x", subject, left, 65536) != ProtectionKey.build(
        "x", subject, right, 65536
    )


def test_canonical_order_defaults_decimal_and_extended_values(subject):
    left = {
        "nested": {"z": 1, "a": 2},
        "items": {3, 2, 1},
        "money": Decimal("12345678901234567890.000"),
    }
    right = {
        "money": Decimal("12345678901234567890"),
        "items": {1, 3, 2},
        "nested": {"a": 2, "z": 1},
    }
    with localcontext() as ctx:
        ctx.prec = 3
        assert ProtectionKey.build("x", subject, left, 65536) == ProtectionKey.build(
            "x", subject, right, 65536
        )
    result = ProtectionKey.build(
        "x", subject, [UUID(int=1), datetime(2026, 1, 1, tzinfo=timezone.utc), b"secret"], 65536
    )
    assert len(result) == 64 and "secret" not in result


@pytest.mark.parametrize("value", [float("nan"), Decimal("Infinity"), object()])
def test_unsupported_inputs_are_explicit(subject, value):
    with pytest.raises((ValueError, TypeError)):
        ProtectionKey.build("x", subject, value, 65536)


def test_cycle_and_length_limit(subject):
    cycle = []
    cycle.append(cycle)
    with pytest.raises(ValueError):
        ProtectionKey.build("x", subject, cycle, 65536)
    with pytest.raises(ValueError):
        ProtectionKey.build("x", subject, "a" * 2000, 256)


@pytest.mark.parametrize(
    "overrides",
    [
        {"rate_limit": {"capacity": 0}},
        {"rate_limit": {"window_ms": True}},
        {"io_timeout_seconds": float("inf")},
        {"lock": {"wait_ms": -1}},
        {"lock": {"execution_timeout_ms": 30000}},
        {"idempotency": {"ttl_ms": 0}},
        {"idempotency": {"max_lifetime_ms": 100}},
        {"key_prefix": "not:valid:*"},
        {"rate_failure_policy": "memory"},
    ],
)
def test_invalid_config_is_rejected(settings, overrides):
    with pytest.raises(ValidationError):
        settings(**overrides)


def test_all_deployment_defaults_are_required(settings):
    options = settings()
    values = options.model_dump()
    for field in type(options).model_fields:
        missing = values.copy()
        del missing[field]
        with pytest.raises(ValidationError):
            type(options).model_validate(missing)


@pytest.mark.parametrize(
    "decorator",
    [
        rate_limit("test"),
        idempotent("test", parameters=("value",)),
        distributed_lock("test", parameters=("value",)),
    ],
)
def test_signature_return_annotations_and_async_contract(decorator):
    async def original(request, value: int = 3) -> str:
        return str(value)

    wrapped = decorator(original)
    assert inspect.signature(wrapped) == inspect.signature(original)
    assert wrapped.__wrapped__ is original
    with pytest.raises(TypeError):
        decorator(lambda value: value)


def test_parameter_boundary_and_failure_list_reject_ambiguity():
    with pytest.raises(ValueError):
        idempotent("test", parameters=(), release_on=(Exception,))

    async def target(request, payload):
        return payload

    for names in [("missing",), ("payload", "payload")]:
        with pytest.raises(ValueError):
            idempotent("test", parameters=names)(target)
