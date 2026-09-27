import pytest
from redis.exceptions import AuthenticationError, AuthorizationError, ResponseError
from redis.exceptions import ConnectionError as RedisConnectionError

from framework.starter_cache.exception.redis_recovery import RedisRecovery


@pytest.mark.parametrize("error_type", [AuthenticationError, AuthorizationError])
@pytest.mark.parametrize("wrapper", [None, RuntimeError, RedisConnectionError])
def test_credentials_are_never_retried_even_inside_connection_errors(error_type, wrapper):
    error = error_type("invalid credentials or ACL")
    if wrapper is not None:
        wrapped = wrapper("request failed")
        wrapped.__cause__ = error
        error = wrapped
    assert RedisRecovery.retryable(error) is False


def test_group_requires_every_error_to_be_recoverable():
    transient = ExceptionGroup("temporary", [RedisConnectionError(), TimeoutError()])
    assert RedisRecovery.retryable(transient) is True
    permanent = ExceptionGroup("mixed", [transient, AuthorizationError()])
    assert RedisRecovery.retryable(permanent) is False
    wrapped = RuntimeError("worker failed")
    wrapped.__cause__ = permanent
    assert RedisRecovery.retryable(wrapped) is False


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RedisConnectionError(), True),
        (TimeoutError(), True),
        (ResponseError("NOGROUP missing group"), True),
        (ResponseError("WRONGTYPE invalid data"), False),
    ],
)
def test_network_and_missing_group_recovery_remain_available(error, expected):
    wrapped = RuntimeError("operation failed")
    wrapped.__cause__ = error
    assert RedisRecovery.retryable(wrapped) is expected
