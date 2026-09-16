import asyncio
import ssl
from collections import deque
from copy import deepcopy

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from fixtures.config_factory import ConfigFactory
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.config.database_tls_settings import DatabaseTlsSettings
from framework.starter_database.connection.external_database_operator import (
    ExternalDatabaseOperator,
)
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_database.starter.database_starter import DatabaseStarter
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app


def defaults():
    return ConfigFactory.values()["config"]["models"]["database"]


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled": True},
        {"id_strategy": "missing"},
        {"pool": {"size": 0}},
        {"replica_strategy": "magic"},
        {"connect_timeout_seconds": 0},
        {"after_commit_result_limit": 0},
        {"dynamic_refresh_interval_seconds": -1},
    ],
)
def test_invalid_configuration_never_receives_hidden_defaults(changes):
    values = defaults()
    ConfigFactory.merge(values, changes)
    with pytest.raises(ValidationError):
        DatabaseSettings.model_validate(values)


def test_every_database_deployment_setting_is_required():
    values = defaults()
    for field in DatabaseSettings.model_fields:
        incomplete = deepcopy(values)
        del incomplete[field]
        with pytest.raises(ValidationError):
            DatabaseSettings.model_validate(incomplete)


def test_tls_has_certificate_and_hostname_verification():
    settings = DatabaseTlsSettings(ca_file=None, certificate_file=None, private_key_file=None)
    context = settings.create_context()
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    with pytest.raises(ValidationError):
        DatabaseTlsSettings(ca_file="relative.pem", certificate_file=None, private_key_file=None)
    with pytest.raises(ValidationError):
        DatabaseTlsSettings(ca_file=None, certificate_file=None, private_key_file="C:/missing.pem")


async def test_invalid_database_environment_fails_without_revealing_url(config_dir):
    app = create_app(
        base_dir=config_dir(),
        environ={
            "DATABASE_ENABLED": "true",
            "DATABASE_SOURCES": '[{"name":"primary","url":"mysql+aiomysql://root:never-print-this@localhost/test","role":"primary","weight":0,"pool":null,"tls":null}]',
        },
    )
    with pytest.raises(BootstrapError) as error:
        async with app.router.lifespan_context(app):
            pass
    assert isinstance(error.value.__cause__, BootstrapConfigError)
    assert "never-print-this" not in str(error.value.__cause__)


async def test_external_database_query_bounds_and_connection_cleanup(database_settings):
    url = database_settings.sources[0].url
    await ExternalDatabaseOperator.test_connection(url, timeout_seconds=2)
    assert await ExternalDatabaseOperator.fetch_all(
        url, text("SELECT 1"), {}, max_rows=1, timeout_seconds=2
    ) == [(1,)]
    with pytest.raises(ValueError, match="条数"):
        await ExternalDatabaseOperator.fetch_all(
            url, text("SELECT 1 UNION ALL SELECT 2"), {}, max_rows=1, timeout_seconds=2
        )


async def test_audit_provider_soft_delete_toggle_and_generated_id_scope(database_case):
    database, Item, mapper = database_case

    class Account:
        def get_current_account_id(self):
            return "provider-account"

    database.bind_account_provider(Account())
    with database.scope() as frame:
        item = await mapper.insert(Item(value="audit"))
        assert item.creator == "provider-account" and frame.generated_ids == [item.id]
    with database.options(account_id="manual"):
        await mapper.update_by_condition({"value": "manual"}, Item.id == item.id)
    assert (await mapper.select_by_id(item.id)).updater == "manual"
    await mapper.delete_by_id(item.id)
    previous = mapper.session_provider
    disabled = SessionProvider(
        database.settings.model_copy(update={"soft_delete_enabled": False, "audit_enabled": False})
    )
    try:
        async with disabled.lifespan():
            mapper.session_provider = disabled
            assert (await mapper.select_by_id(item.id)).deleted
            with disabled.scope(account_id="not-stored"):
                created = await mapper.insert(Item(value="audit-off"))
                assert created.creator == "" and created.create_time is not None
    finally:
        mapper.session_provider = previous


async def test_expired_value_scope_does_not_escape_to_later_task(database_case):
    database, Item, mapper = database_case
    release = asyncio.Event()

    async def delayed():
        await release.wait()
        return await mapper.count()

    with database.scope(account_id="old"):
        task = asyncio.create_task(delayed())
    release.set()
    with pytest.raises(DatabaseException):
        await task


async def test_background_callback_results_are_bounded_and_bad_contract_rejected(database_case):
    database, Item, mapper = database_case
    database._transactions.results = deque(maxlen=2)

    def callback():
        raise ValueError("private failure detail")

    for index in range(3):
        database.after_commit(callback, required=False, name=f"callback-{index}")
    await database._transactions.drain_callbacks()
    results = database.get_metrics()["after_commit"]
    assert len(results) == 2 and all(result.error_type == "ValueError" for result in results)
    assert "private failure detail" not in repr(results)

    def generator():
        yield 1

    with pytest.raises(TypeError):
        database.after_commit(generator, required=False)


async def test_loader_preflight_publication_and_periodic_refresh(database_settings, config_dir):
    from fixtures.starter_steps import StarterSteps

    values = database_settings.model_dump(mode="json")
    for source, actual in zip(values["sources"], database_settings.sources):
        source["url"] = actual.url.get_secret_value()
    values["dynamic_refresh_interval_seconds"] = 0.02
    app = create_app(
        steps=StarterSteps.without_tenant(),
        base_dir=config_dir(
            {"config": {"models": {"database": values}}, "banner": {"enabled": False}}
        ),
        environ={},
    )
    source = database_settings.sources[0].model_copy(update={"name": "reporting", "role": "named"})

    class Loader:
        sources = (source,)

        async def load_sources(self):
            return self.sources

    async with app.router.lifespan_context(app):
        application = app.state.application_context
        with application.execution():
            starter = application.container.get(DatabaseStarter)
            loader = Loader()
            await starter.attach_source_loader(loader)
            assert app.state.database.get_metrics()["revision"] == 2
            loader.sources = ()
            assert await starter.refresh_sources(preflight=True) == 2
        async with asyncio.timeout(2):
            while app.state.database.get_metrics()["revision"] < 3:
                await asyncio.sleep(0.01)
        assert "reporting" not in app.state.database.get_metrics()["pools"]
