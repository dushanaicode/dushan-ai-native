import pytest

from framework.starter_mq.backend import rabbit_backend
from framework.starter_mq.backend.rabbit_backend import RabbitBackend
from framework.starter_mq.definitions.constants.mq_error_codes import MQErrorCodes
from framework.starter_mq.exception.mq_exception import MQException
from starter_mq.test_declarations import settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.2.9", (4, 2, 9)),
        ("3.12.1", (3, 12, 1)),
        ("4.2", (4, 2, 0)),
        ("4", (4, 0, 0)),
        ("4.2.9-beta.1", (4, 2, 9)),
        ("4.2.9+build.7", (4, 2, 9)),
    ],
)
def test_parse_version_reads_numeric_prefix(raw, expected):
    assert RabbitBackend._parse_version(raw) == expected


@pytest.mark.parametrize(
    ("properties", "accepted"),
    [
        ({"product": "RabbitMQ", "version": "4.2.9"}, True),
        ({"product": "RabbitMQ", "version": "4.3.0"}, True),
        ({"product": "RabbitMQ", "version": "5.0.0"}, True),
        ({"product": "RabbitMQ", "version": "4.2.8"}, False),
        ({"product": "RabbitMQ", "version": "3.12.1"}, False),
        ({"product": "SomeOtherBroker", "version": "9.9.9"}, False),
        ({"product": "RabbitMQ", "version": None}, False),
        ({"product": "RabbitMQ"}, False),
        ({}, False),
    ],
)
def test_check_broker_version_matches_minimum_supported(properties, accepted):
    backend = RabbitBackend("prefix", settings(backend="rabbitmq"))
    if accepted:
        backend._check_broker_version(properties)
    else:
        with pytest.raises(MQException) as failure:
            backend._check_broker_version(properties)
        assert failure.value.error_code is MQErrorCodes.CONFIGURATION


@pytest.mark.parametrize("mq_backend", ["rabbitmq"], indirect=True)
async def test_open_rejects_broker_below_minimum_version_and_closes_connection(
    mq_case, monkeypatch
):
    """真实连到当前已配置的 RabbitMQ 实例；临时把最低版本要求提到不可能满足，
    验证真实握手拿到的 server_properties 触发拒绝，且原始连接确实被关闭，
    不会带着一个已经握手成功但未声明队列的连接继续运行。"""
    case = mq_case
    monkeypatch.setattr(rabbit_backend, "MINIMUM_BROKER_VERSION", (99, 0, 0))
    backend = RabbitBackend("n1-reject-probe", case.runtime.settings)
    with pytest.raises(MQException) as failure:
        await backend.open([])
    assert failure.value.error_code is MQErrorCodes.CONFIGURATION
    assert backend.connection is None
