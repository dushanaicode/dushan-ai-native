from dataclasses import replace

import pytest
from pydantic import BaseModel, ValidationError

from fixtures.config_factory import ConfigFactory
from framework.starter_mq.config.mq_settings import MQSettings
from framework.starter_mq.core.consumer_registry import ConsumerRegistry
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.definitions.enums.exhausted_policy import ExhaustedPolicy
from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.definitions.enums.tenant_policy import TenantPolicy
from framework.starter_mq.exception.mq_exception import MQException
from framework.starter_mq.model.consumer_definition import ConsumerDefinition
from framework.starter_mq.model.consumer_override import ConsumerOverride
from framework.starter_mq.model.retry_policy import RetryPolicy
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app
from starter_mq.conftest import SOURCE


class Payload(BaseModel):
    value: int


def settings(**changes):
    values = ConfigFactory.values()["config"]["models"]["mq"]
    return MQSettings.model_validate({**values, **changes})


def definition(**changes):
    value = ConsumerDefinition(
        key="one",
        destination="events",
        mode=MessageMode.STREAM,
        message=Payload,
        group="workers",
        retry=RetryPolicy(count=1, delay_seconds=1, backoff=2, max_delay_seconds=4),
        exhausted=ExhaustedPolicy.DEAD_LETTER,
        tenant_policy=TenantPolicy.GLOBAL,
        session_policy=None,
        workload_capabilities=frozenset(("consume",)),
    )
    return replace(value, **changes)


def handler(declaration):
    return type("Handler", (), {"__mq_consumer__": declaration})


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": MessageMode.PUBSUB, "group": None},
        {"mode": MessageMode.QUEUE, "group": None},
        {"group": None},
        {"workload_capabilities": frozenset()},
    ],
)
def test_unsupported_semantics_rejected(changes):
    with pytest.raises(MQException) as failure:
        ConsumerRegistry(settings(), [handler(definition(**changes))])
    assert failure.value.error_code is MQErrorCodes.DECLARATION


def test_duplicate_key_and_different_keys_sharing_work_queue_rejected():
    for second in (definition(), definition(key="two")):
        with pytest.raises(MQException):
            ConsumerRegistry(settings(), [handler(definition()), handler(second)])


def test_deployment_overrides_are_restricted_and_unknown_is_explicit():
    with pytest.raises(ValidationError):
        ConsumerOverride(enabled=True, concurrency=None, prefetch=None, destination="other")
    registry = ConsumerRegistry(settings(), [handler(definition())])
    override = ConsumerOverride(enabled=False, concurrency=1, prefetch=2)
    with pytest.raises(MQException) as failure:
        registry.apply({"missing": override})
    assert "missing" in " ".join(failure.value.__notes__)
    registry = ConsumerRegistry(settings(unknown_override="ignore"), [handler(definition())])
    registry.apply({"missing": override, "one": override})
    assert registry.ignored_overrides == ("missing",)
    assert registry.active() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled": True},
        {"renew_seconds": 60},
        {"replay_retention_seconds": 1},
        {"prefetch": 1},
        {"kafka_sasl_username": "partial"},
    ],
)
def test_invalid_configuration_fails_before_resources(changes):
    with pytest.raises(ValidationError):
        settings(**changes)


async def test_disabled_configuration_does_not_open_broker(config_dir, monkeypatch):
    from framework.starter_mq.backend.redis_backend import RedisBackend

    async def forbidden(*args):
        raise AssertionError("disabled MQ connected")

    monkeypatch.setattr(RedisBackend, "open", forbidden)
    app = create_app(base_dir=config_dir({"banner": {"enabled": False}}), environ={})
    async with app.router.lifespan_context(app):
        assert app.state.mq is None


async def test_duplicate_key_fails_real_bootstrap(config_dir, module_package):
    source = (
        SOURCE.replace("__MODE__", "stream")
        .replace("__GROUP__", '"workers"')
        .replace("__RETRIES__", "1")
        .replace("__EXHAUSTED__", "dead_letter")
        .replace("__TENANT__", "global")
        .replace("__EXTERNAL__", "None")
    )
    source = source.replace("__SQL_QUERY__", "")
    source += "\n@consumer(definition)\nclass Duplicate(Controlled):\n    pass\n"
    module_package(
        "duplicate_mq", name="duplicate_mq", scan_roots=(".",), files={"components.py": source}
    )
    app = create_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {
                    "packages": ["framework", "duplicate_mq"],
                    "enabled": ["framework", "duplicate_mq"],
                },
            }
        ),
        environ={},
    )
    with pytest.raises(BootstrapError) as failure:
        async with app.router.lifespan_context(app):
            pytest.fail("duplicate key started")
    assert isinstance(failure.value.__cause__, MQException)
