import asyncio
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest
from sqlalchemy import bindparam, literal_column, select

from fixtures.config_factory import ConfigFactory
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.connection.connection_factory import ConnectionFactory
from framework.starter_database.connection.replication_status import ReplicationStatus
from framework.starter_database.connection.sql_template import SqlTemplate
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider


@pytest.fixture
def observation_settings(tmp_path):
    values = ConfigFactory.values()["config"]["models"]["database"]
    values.update(
        enabled=True,
        health_check_enabled=False,
        slow_query_enabled=False,
        query_observation_enabled=True,
        query_template_enabled=True,
        query_fingerprint_enabled=True,
        query_sample_rate=1.0,
        sources=[
            dict(
                name="primary",
                url=f"sqlite+aiosqlite:///{(tmp_path / 'observation.sqlite').as_posix()}",
                role="primary",
                weight=100,
                pool=None,
                tls=None,
            )
        ],
    )
    return DatabaseSettings.model_validate(values)


def contains_error(group, expected):
    return group is expected or (
        isinstance(group, BaseExceptionGroup)
        and any(contains_error(error, expected) for error in group.exceptions)
    )


async def test_monitor_crash_degrades_readiness_and_survives_until_close(
    observation_settings, monkeypatch
):
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "health_check_enabled": True,
                "health_check_interval_seconds": 0.001,
            }
        )
    )
    defect = RuntimeError("monitor defect")

    async def crash():
        raise defect

    monkeypatch.setattr(database, "check_health", crash)
    await database.open()
    try:
        await asyncio.wait({database._monitor}, timeout=2)
        assert not database.is_ready
        status = database.get_metrics()["monitor"]
        assert status["state"] == "failed" and status["error_type"] == "RuntimeError"
        assert status["started_at"] <= status["round_started_at"] <= status["finished_at"]
        assert status["checked_at"] is None
    finally:
        with pytest.raises(BaseExceptionGroup) as captured:
            await database.close()
    assert contains_error(captured.value, defect)
    assert database.get_metrics()["pools"] == {}
    assert database.get_metrics()["monitor"]["state"] == "failed"


async def test_monitor_updates_health_time_and_normal_close_is_not_failure(
    observation_settings, monkeypatch
):
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "health_check_enabled": True,
                "health_check_interval_seconds": 0.001,
            }
        )
    )
    checked = asyncio.Event()
    original = database.check_health

    async def check():
        result = await original()
        checked.set()
        return result

    monkeypatch.setattr(database, "check_health", check)
    await database.open()
    try:
        await asyncio.wait_for(checked.wait(), timeout=2)
        status = database.get_metrics()["monitor"]
        assert database.is_ready and status["state"] == "running"
        assert status["checked_at"] >= status["round_started_at"]
    finally:
        await database.close()
    assert database.get_metrics()["monitor"]["state"] == "stopped"
    assert database.get_metrics()["monitor"]["error_type"] is None
    assert not database.is_ready


async def test_external_monitor_cancel_is_not_hidden_by_immediate_close(observation_settings):
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "health_check_enabled": True,
            }
        )
    )
    await database.open()
    database._monitor.cancel()
    with pytest.raises(BaseExceptionGroup):
        await database.close()
    assert database.get_metrics()["monitor"]["state"] == "failed"
    assert database.get_metrics()["pools"] == {}


async def test_connectivity_and_replication_health_remain_independent(
    observation_settings, monkeypatch
):
    primary = observation_settings.sources[0]
    replica = primary.model_copy(update={"name": "replica", "role": "replica"})
    status = {"running": False, "lag_seconds": 0}

    async def replication(entry):
        return dict(status)

    monkeypatch.setattr(ReplicationStatus, "read", replication)
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "sources": (primary, replica),
                "replication_check_enabled": True,
            }
        )
    )
    async with database.lifespan():
        assert (await database.check_health())["replica"] is False
        async with database.read_session():
            assert database.get_metrics()["pools"]["primary"]["leases"] == 1
        status["running"] = True
        await database.check_replication()
        async with database.read_session():
            assert database.get_metrics()["pools"]["replica"]["leases"] == 1
        original = ConnectionFactory.probe

        async def disconnected(engine):
            if engine is database._registry.entries["replica"].engine:
                raise OSError("unreachable")
            await original(engine)

        monkeypatch.setattr(ConnectionFactory, "probe", disconnected)
        await database.check_health()
        await database.check_replication()
        pool = database.get_metrics()["pools"]["replica"]
        assert not pool["connected"] and pool["replication_healthy"] and not pool["healthy"]
        monkeypatch.setattr(ConnectionFactory, "probe", original)
        assert (await database.check_health())["replica"] is True


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT 'secret_one''secret_two', E'secret_three\\\\secret_four'",
        "SELECT 'secret_backslash\\'secret_after_escape'",
        'SELECT "secret_identifier", `secret_backtick`, [secret_bracket]]secret_tail]',
        "SELECT $$secret_dollar ' nested $$, $tag$secret_tag$tag$",
        "SELECT 982173, 0xdeadbeef, 7.821e-19, X'736563726574'",
        "SELECT :secret_bind, %(secret_pyformat)s, @secret_named, $1, ?2",
        "SELECT /* secret_comment /* secret_nested */ secret_tail */ ? -- secret_line\n",
        "SELECT 'unterminated_secret",
        "SELECT $private$unterminated_secret",
        "SELECT literal_column_secret FROM secret_table # secret_mysql_comment",
    ],
)
def test_sql_template_never_preserves_untrusted_tokens(statement):
    operation, template = SqlTemplate.render(statement, max_length=65536)
    assert operation == "SELECT"
    assert "secret" not in template.lower()
    assert "982173" not in template and "deadbeef" not in template and "7.821" not in template


async def test_safe_events_cover_bindings_literal_columns_and_failed_sql(observation_settings):
    observations = []
    database = SessionProvider(observation_settings)
    async with database.lifespan():
        database.bind_query_observer(SimpleNamespace(observe=observations.append))
        async with database.read_session() as session:
            for value in ("binding_secret_one", "binding_secret_two"):
                assert await session.scalar(select(bindparam("value")), {"value": value}) == value
            assert await session.scalar(
                select(literal_column("'inline_secret''escaped_secret'"))
            ) == ("inline_secret'escaped_secret")
        with pytest.raises(DatabaseException):
            async with database.read_session() as session:
                await session.scalar(select(literal_column("missing_secret_column")))
        events = [event for event in observations if event.operation == "SELECT"]
        assert [event.success for event in events] == [True, True, True, False]
        assert events[0].fingerprint == events[1].fingerprint
        assert events[0].fingerprint is not None
        assert all("secret" not in repr(event) for event in events)
        assert all(event.elapsed_ms >= 0 and event.source == "primary" for event in events)
        with pytest.raises(FrozenInstanceError):
            events[0].template = "unsafe"


@pytest.mark.parametrize(
    "changes",
    [
        {"query_observation_enabled": False},
        {"query_sample_rate": 0.0},
    ],
)
async def test_disabled_or_unsampled_queries_do_not_notify(observation_settings, changes):
    observations = []
    database = SessionProvider(observation_settings.model_copy(update=changes))
    database.bind_query_observer(SimpleNamespace(observe=observations.append))
    async with database.lifespan():
        async with database.read_session() as session:
            assert await session.scalar(select(literal_column("42"))) == 42
        assert observations == []


async def test_template_and_fingerprint_switches_and_output_bounds(observation_settings):
    observations = []
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "query_template_enabled": False,
                "query_fingerprint_enabled": False,
            }
        )
    )
    async with database.lifespan():
        database.bind_query_observer(SimpleNamespace(observe=observations.append))
        async with database.read_session() as session:
            assert await session.scalar(select(literal_column("'sensitive'"))) == "sensitive"
    assert all(event.template is None and event.fingerprint is None for event in observations)
    observations.clear()
    database = SessionProvider(
        observation_settings.model_copy(
            update={
                "query_max_statement_length": 64,
                "query_max_template_length": 16,
            }
        )
    )
    async with database.lifespan():
        database.bind_query_observer(SimpleNamespace(observe=observations.append))
        async with database.read_session() as session:
            await session.scalar(select(literal_column("1 + 2 + 3 + 4 + 5 + 6")))
            await session.scalar(select(literal_column("'" + "sensitive" * 20 + "'")))
    events = [event for event in observations if event.operation in ("SELECT", "UNKNOWN")]
    assert any(event.template is not None and len(event.template) == 16 for event in events)
    assert any(event.template is None and event.fingerprint is None for event in events)
    assert all(event.template is None or len(event.template) <= 16 for event in events)


@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
async def test_observer_failure_does_not_change_commit(database_case, error_type):
    database, Item, mapper = database_case

    def fail(observation):
        raise error_type("consumer_secret")

    database.bind_query_observer(SimpleNamespace(observe=fail))
    async with database.transaction():
        await mapper.insert(Item(value="committed despite observer"))
    assert await mapper.count() == 1
    metrics = database.get_metrics()["query_observation"]
    assert metrics["failures"] > 0 and metrics["last_error_type"] == error_type.__name__
    assert "consumer_secret" not in repr(database.get_metrics())
    database.bind_query_observer(None)
