import pytest

from fixtures.config_factory import ConfigFactory
from framework.starter_ip.config.ip_settings import IpSettings


@pytest.fixture
def ip_settings():
    def create(**overrides):
        values = ConfigFactory.values()["config"]["models"]["ip"]
        return IpSettings.model_validate({**values, "enabled": True, **overrides})

    return create
