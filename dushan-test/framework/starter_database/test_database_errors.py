import asyncio
import json
import traceback
from io import StringIO

import pytest
from loguru import logger
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.requests import Request

from framework.common.diagnostics.exception_trace_formatter import ExceptionTraceFormatter
from framework.common.diagnostics.safe_exception_diagnostics import SafeExceptionDiagnostics
from framework.common.exception.core.exception_handler import GlobalExceptionHandler
from framework.common.exception.utils.response_builder import ExceptionResponseBuilder
from framework.starter_database.exception.after_commit_exception import AfterCommitException
from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.managed_async_session import ManagedAsyncSession
from framework.starter_logging.core.logger_configurator import LoggerConfigurator


def driver_error(*, state=None, code=None):
    original = Exception("opaque-private-row postgresql://private-user:private-pass@db/private-db")
    if state is not None:
        original.sqlstate = state
    if code is not None:
        original.args = (code, original.args[0])
    return DBAPIError(
        "INSERT INTO private_table VALUES ('opaque-private-sql')",
        {"value": "opaque-private-param"},
        original,
    )


@pytest.mark.parametrize(
    ("dialect", "state", "code", "category", "retryable"),
    [
        ("postgresql", "23505", None, "unique", False),
        ("postgresql", "23503", None, "foreign_key", False),
        ("postgresql", "23502", None, "not_null", False),
        ("postgresql", "23514", None, "check", False),
        ("kingbase", "42601", None, "programming", False),
        ("opengauss", "08006", None, "connection", False),
        ("postgresql", "57014", None, "statement_cancelled", False),
        ("postgresql", "40001", None, "serialization", True),
        ("postgresql", "40P01", None, "deadlock", True),
        ("mysql", "40001", 1213, "deadlock", True),
        ("mysql", "HY000", 1205, "statement_timeout", False),
        ("oceanbase", "23000", 1062, "unique", False),
        ("mysql", "23000", 1452, "foreign_key", False),
        ("mysql", "23000", 1048, "not_null", False),
        ("mysql", "HY000", 3819, "check", False),
        ("mysql", "HY000", 2013, "connection", False),
        ("dm", None, -6602, "unique", False),
        ("dm", None, -6603, "foreign_key", False),
        ("dm", None, -6604, "check", False),
        ("dm", None, -6606, "not_null", False),
        ("dm", None, -6407, "statement_timeout", False),
        ("dm", None, -2007, "programming", False),
        ("postgresql", "23000", None, "integrity", False),
        ("postgresql", "22003", None, "data", False),
    ],
)
def test_structured_driver_classification(dialect, state, code, category, retryable):
    safe = DatabaseErrorTranslator.translate(driver_error(state=state, code=code), dialect=dialect)
    assert isinstance(safe, DatabaseException)
    assert safe.context["category"] == category
    assert safe.retryable is retryable
    assert "opaque-private" not in repr(vars(safe))
    assert safe.__cause__ is None and safe.__context__ is None


def test_unknown_message_never_implies_duplicate_or_retry():
    unknown = OperationalError("private sql", {}, Exception("duplicate key deadlock timeout"))
    safe = DatabaseErrorTranslator.translate(unknown, dialect="postgresql")
    assert safe.error_code == DatabaseErrorCodes.ERROR
    assert not safe.retryable
    pool = DatabaseErrorTranslator.translate(PoolTimeoutError("private pool url"))
    assert pool.error_code == DatabaseErrorCodes.POOL_TIMEOUT
    assert not pool.retryable
    user_error = ValueError("application input")
    assert DatabaseErrorTranslator.translate(user_error) is user_error


def test_commit_outcome_and_cancellation_are_not_retryable():
    error = driver_error(state="40001")
    assert DatabaseErrorTranslator.translate(error, phase="commit").retryable is False
    cancellation = asyncio.CancelledError()
    group = BaseExceptionGroup("cleanup", [cancellation, error])
    translated = DatabaseErrorTranslator.translate(group, phase="commit")
    assert translated.exceptions[0] is cancellation
    assert translated.exceptions[1].context["category"] == "serialization"
    assert not translated.exceptions[1].retryable
    committed = AfterCommitException()
    assert DatabaseErrorTranslator.translate(committed).committed is True


@pytest.fixture
def sqlite_constraints():
    engine = create_engine("sqlite://")
    DatabaseErrorTranslator.install(engine)
    metadata = MetaData()
    parent = Table(
        "safe_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False, unique=True),
        CheckConstraint("id > 0"),
    )
    child = Table(
        "safe_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey(parent.c.id)),
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        metadata.create_all(connection)
        connection.execute(insert(parent), {"id": 1, "name": "baseline"})
    try:
        yield engine, parent, child
    finally:
        engine.dispose()


@pytest.mark.parametrize("category", ["unique", "foreign_key", "not_null", "check"])
def test_real_constraints_classify_and_rollback_whole_transaction(sqlite_constraints, category):
    engine, parent, child = sqlite_constraints
    statements = {
        "unique": insert(parent).values(id=2, name="baseline"),
        "foreign_key": insert(child).values(id=1, parent_id=999),
        "not_null": insert(parent).values(id=2, name=None),
        "check": insert(parent).values(id=-1, name="invalid"),
    }
    with pytest.raises(DatabaseException) as failure:
        with DatabaseErrorTranslator.boundary(dialect=engine.dialect):
            with engine.begin() as connection:
                connection.execute(insert(parent), {"id": 10, "name": "rolled-back"})
                connection.execute(statements[category])
    assert failure.value.context["category"] == category
    assert failure.value.__cause__ is None and failure.value.__context__ is None
    with engine.connect() as connection:
        assert connection.execute(select(parent.c.id)).scalars().all() == [1]
        assert connection.execute(select(child.c.id)).scalars().all() == []


def test_real_executemany_failure_rolls_back_partial_batch(sqlite_constraints):
    engine, parent, _ = sqlite_constraints
    with pytest.raises(DatabaseException) as failure:
        with DatabaseErrorTranslator.boundary(dialect=engine.dialect):
            with engine.begin() as connection:
                connection.execute(
                    insert(parent),
                    [
                        {"id": 2, "name": "first-batch-row"},
                        {"id": 3, "name": "baseline"},
                    ],
                )
    assert failure.value.error_code == DatabaseErrorCodes.UNIQUE_VIOLATION
    with engine.connect() as connection:
        assert connection.execute(select(parent.c.name)).scalars().all() == ["baseline"]


def unsafe_chained_failure():
    original = driver_error(state="23505")
    safe = DatabaseErrorTranslator.translate(original, dialect="postgresql")
    # 模拟 SQLAlchemy handle_error 在返回替代异常后强制挂接的原始原因。
    safe.__cause__ = original
    safe.__context__ = original.orig
    return safe


@pytest.mark.parametrize("debug", [False, True])
async def test_http_response_and_third_party_trace_never_receive_raw_driver(debug):
    received = []
    reporter = type("Reporter", (), {"on_error": staticmethod(received.append)})()
    handler = GlobalExceptionHandler(debug=debug, trace_reporter=reporter)
    error = unsafe_chained_failure()
    response = await handler.handle_business_exception(
        Request({"type": "http", "path": "/database"}), error
    )
    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["code"] == DatabaseErrorCodes.UNIQUE_VIOLATION.code
    assert bool(payload["error"] and "debug" in payload["error"]) is debug
    exported = received[0]
    assert exported is not error
    assert (
        exported.__cause__ is None
        and exported.__context__ is None
        and exported.__traceback__ is None
    )
    serialized = (
        response.body.decode()
        + "".join(traceback.format_exception(exported))
        + repr(vars(exported))
    )
    for secret in ("private-user", "private-pass", "private_table", "opaque-private"):
        assert secret not in serialized


@pytest.mark.parametrize("grouped", [False, True])
def test_loguru_and_debug_group_trace_exclude_raw_cause_and_source(grouped):
    error = unsafe_chained_failure()
    if grouped:
        wrapper = RuntimeError("opaque-private-wrapper")
        wrapper.__cause__ = error
        error = ExceptionGroup("opaque-private-group", [wrapper, error])
    output = StringIO()
    sink = logger.add(
        output, format="{message}{extra[exception_trace]}", backtrace=True, diagnose=True
    )
    try:
        logger.patch(LoggerConfigurator._patch_record).opt(exception=error).error("数据库操作失败")
    finally:
        logger.remove(sink)
    payload = ExceptionResponseBuilder.build(
        DatabaseErrorCodes.ERROR, "数据库操作失败", exc=error, debug=True
    )
    serialized = (
        output.getvalue() + json.dumps(payload) + "".join(ExceptionTraceFormatter.format(error))
    )
    assert "DatabaseException" in output.getvalue()
    for secret in ("private-user", "private-pass", "private_table", "opaque-private"):
        assert secret not in serialized


def test_safe_diagnostics_retains_after_commit_and_cleanup_failure_classes():
    committed = AfterCommitException()
    committed.__cause__ = ExceptionGroup(
        "opaque-private-group", [unsafe_chained_failure(), RuntimeError("opaque-private-row")]
    )
    safe = SafeExceptionDiagnostics.snapshot(committed)
    assert safe.committed and not safe.retryable
    rendered = "".join(traceback.format_exception(safe))
    assert "RuntimeError" in rendered and "DatabaseException" in rendered
    assert "opaque-private" not in rendered


async def test_managed_flush_integrity_failure_keeps_transaction_atomic(database_case):
    database, Item, mapper = database_case
    with pytest.raises(DatabaseException) as failure:
        async with database.transaction() as session:
            first = Item(value="first")
            session.add(first)
            await session.flush()
            identifier = first.id
            session.expunge(first)
            session.add(Item(id=identifier, value="second"))
            await session.flush()
    assert failure.value.error_code == DatabaseErrorCodes.UNIQUE_VIOLATION
    assert await mapper.count() == 0


async def test_commit_acknowledgement_loss_never_retries_or_claims_rollback(
    database_case, monkeypatch
):
    database, Item, mapper = database_case
    commit = ManagedAsyncSession.commit
    attempts = []

    async def lost_acknowledgement(session):
        await commit(session)
        attempts.append(1)
        raise driver_error(state="08006")

    with monkeypatch.context() as patch:
        patch.setattr(ManagedAsyncSession, "commit", lost_acknowledgement)
        with pytest.raises(DatabaseException) as failure:
            async with database.transaction():
                await mapper.insert(Item(value="committed-before-disconnect"))
    assert failure.value.error_code == DatabaseErrorCodes.CONNECTION_FAILED
    assert failure.value.context["phase"] == "commit"
    assert not failure.value.retryable
    assert not getattr(failure.value, "committed", False)
    assert attempts == [1]
    assert await mapper.count() == 1
