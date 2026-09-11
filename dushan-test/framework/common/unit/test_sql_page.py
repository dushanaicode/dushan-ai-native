import pytest
import pytest_asyncio
from config_factory import ConfigFactory
from sqlalchemy import String, event, func, select, text
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from framework.common.exception.exceptions.illegal_argument_exception import (
    IllegalArgumentException,
)
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.common.page.schemas.page_query import PageQuery
from framework.common.page.schemas.sortable_page_query import SortablePageQuery

pytestmark = pytest.mark.unit


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "page_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(20))


@pytest_asyncio.fixture
async def database(tmp_path):
    """在测试Temp内创建真实异步数据库，连接生命周期由fixture管理。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'page.sqlite').as_posix()}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            session.add_all(
                [
                    Record(id=1, name="Beta", category="b"),
                    Record(id=2, name="Alpha", category="a"),
                    Record(id=3, name="Alpha", category="a"),
                    Record(id=4, name="Gamma", category="b"),
                ]
            )
        yield engine, factory
    finally:
        await engine.dispose()


async def test_sql_page_counts_filters_and_retains_total_for_empty_page(database):
    """查询总数与当前页来自真实SQL，过滤、末页和空集均保留正确语义。"""
    _, factory = database
    paginator = DataPaginator(ConfigFactory.build(PageSettings, "page", default_size=2))
    query = select(Record).order_by(Record.id)
    async with factory() as session:
        result = await paginator.paginate_query(session, query, PageQuery(page=2))
        assert [row.id for row in result.items] == [3, 4]
        assert result.total == 4
        empty = await paginator.paginate_query(session, query, PageQuery(page=4))
        assert empty.items == [] and empty.total == 4
        filtered = await paginator.paginate_query(session, query.where(Record.category == "a"))
        assert [row.id for row in filtered.items] == [2, 3] and filtered.total == 2
        absent = await paginator.paginate_query(session, query.where(Record.id == 99))
        assert absent.items == [] and absent.total == 0
        assert await session.scalar(select(func.count()).select_from(Record)) == 4


@pytest.mark.parametrize(
    "query",
    [
        select(Record.category).distinct().order_by(Record.category),
        select(Record.category).group_by(Record.category).order_by(Record.category),
    ],
)
async def test_sql_count_preserves_distinct_and_grouping(database, query):
    """计数基于原查询结果集合，不把去重或分组数量误算成表行数。"""
    _, factory = database
    async with factory() as session:
        result = await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
            session, query, PageQuery(pageSize=1)
        )
    assert result.items == ["a"] and result.total == 2


async def test_sql_sorting_uses_columns_and_explicit_stable_tie_breaker(database):
    """客户端只能选择服务端列映射，同值结果使用明确唯一键保持顺序。"""
    _, factory = database
    query = SortablePageQuery(pageSize=2, sortingFields=[{"field": "name", "order": "asc"}])
    async with factory() as session:
        result = await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
            session,
            select(Record).order_by(Record.id.desc()),
            query,
            sort_columns={"name": Record.name},
            order_by=(Record.id,),
        )
    assert [row.id for row in result.items] == [2, 3] and result.total == 4


async def test_sql_policy_errors_happen_before_database_io(database):
    """大小、排序白名单、全量开关和多列投影错误不能先执行SQL。"""
    engine, factory = database
    calls = []
    event.listen(engine.sync_engine, "before_cursor_execute", lambda *args: calls.append(args[2]))
    async with factory() as session:
        with pytest.raises(IllegalArgumentException):
            await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
                session, select(Record), PageQuery(pageSize=201)
            )
        with pytest.raises(IllegalArgumentException):
            await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
                session, select(Record), PageQuery().enable_fetch_all()
            )
        with pytest.raises(IllegalArgumentException):
            await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
                session, select(Record), SortablePageQuery(sortingFields=[{"field": "private"}])
            )
        with pytest.raises(ValueError, match="单个实体"):
            await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
                session, select(Record.id, Record.name)
            )
    assert calls == []


async def test_sql_fetch_all_applies_limit_and_never_commits_the_callers_transaction(database):
    """全量查询有硬限制，分页器不会提交调用方尚未提交的写入。"""
    engine, factory = database
    statements = []
    event.listen(
        engine.sync_engine,
        "before_cursor_execute",
        lambda *args: statements.append((args[2], args[3])),
    )
    paginator = DataPaginator(
        ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True, fetch_all_max_rows=5)
    )
    async with factory() as session:
        session.add(Record(id=5, name="Pending", category="a"))
        result = await paginator.paginate_query(
            session, select(Record).order_by(Record.id), PageQuery().enable_fetch_all()
        )
        assert result.total == len(result.items) == 5
        assert any("LIMIT" in sql and parameters == (6, 0) for sql, parameters in statements)
        assert session.in_transaction()
        await session.rollback()
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Record)) == 4


async def test_sql_fetch_all_detects_actual_growth_after_count(database):
    """COUNT后出现新行时，LIMIT上限+1仍能识别超限而不是无界读取。"""
    engine, factory = database
    inserted = False

    def after_count(connection, cursor, statement, parameters, context, executemany):
        nonlocal inserted
        if not inserted and statement.startswith("SELECT count("):
            inserted = True
            connection.execute(Record.__table__.insert().values(id=5, name="Late", category="a"))

    event.listen(engine.sync_engine, "after_cursor_execute", after_count)
    paginator = DataPaginator(
        ConfigFactory.build(PageSettings, "page", fetch_all_enabled=True, fetch_all_max_rows=4)
    )
    async with factory() as session:
        with pytest.raises(IllegalArgumentException, match="最多允许 4 条"):
            await paginator.paginate_query(
                session, select(Record).order_by(Record.id), PageQuery().enable_fetch_all()
            )
        assert session.in_transaction()
        await session.rollback()


async def test_sql_errors_propagate_without_closing_the_session(database):
    """数据库错误由事务所有者处理，不被分页器包装成空结果。"""
    _, factory = database
    async with factory() as session:
        with pytest.raises(OperationalError):
            await DataPaginator(ConfigFactory.build(PageSettings, "page")).paginate_query(
                session, select(Record).where(text("missing_column = 1"))
            )
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(Record)) == 4


@pytest.mark.parametrize("dialect", [mysql.dialect(), postgresql.dialect()])
def test_target_sql_dialects_compile_bound_pagination(dialect):
    """检查目标方言参数化分页形状，真实服务器验收与本地SQLite验证分开报告。"""
    statement = (
        select(Record).where(Record.name == "' OR 1=1 --").order_by(Record.id).limit(2).offset(4)
    )
    compiled = statement.compile(dialect=dialect)
    assert "LIMIT" in str(compiled)
    assert "' OR 1=1 --" not in str(compiled)
    assert set(compiled.params.values()) == {"' OR 1=1 --", 2, 4}
