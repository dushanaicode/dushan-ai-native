import pytest

from fixtures.config_factory import ConfigFactory
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.core.di_container import DiContainer


@pytest.fixture
def contexts(config_dir):
    provider = ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [])

    def make(components=(), *, instances=None, **settings):
        return ApplicationContext(
            DiContainer(
                components,
                configuration=provider,
                settings=ConfigFactory.build(DiSettings, "di", **settings),
                enabled_modules=frozenset(),
                instances=instances,
            )
        )

    yield make
    provider.close()
