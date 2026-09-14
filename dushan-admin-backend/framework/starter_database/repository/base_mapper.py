from collections.abc import Collection, Mapping
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

from sqlalchemy import (
    Delete,
    Insert,
    Select,
    UniqueConstraint,
    Update,
    delete,
    func,
    inspect,
    select,
    update,
)
from sqlalchemy.sql import visitors
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import SelectBase

from framework.common.page.schemas.page_query import PageQuery
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.pagination.sql_paginator import SqlPaginator
from framework.starter_database.repository.atomic_upsert import AtomicUpsert
from framework.starter_database.session.managed_session import ManagedSession
from framework.starter_database.session.session_provider import SessionProvider
from framework.starter_di.decorators.inject import Inject

T = TypeVar("T")
IMMUTABLE_FIELDS = frozenset(
    {"id", "tenant_id", "creator", "create_time", "updater", "update_time", "deleted"}
)


class BaseMapper(Generic[T]):
    """单主键实体的通用访问；业务子类显式标记 @mapper，并选择模型。

    独立写入自动开启事务，已有事务内复用会话。更新仅写已明确传入的业务字段；
    软删除、物理清理与原始 SQL 分属不同入口，不把任意语句猜成安全读取。
    """

    session_provider: SessionProvider = Inject()
    paginator: SqlPaginator = Inject()

    def __init__(self, model: type[T], datasource: str | None = None) -> None:
        if len(inspect(model).primary_key) != 1:
            raise ValueError("BaseMapper 要求单主键模型")
        self.model, self.datasource = model, datasource

    @asynccontextmanager
    async def _get_session_scope(self, *, for_write=False, force_primary=False):
        scope = (
            self.session_provider.transaction(source=self.datasource)
            if for_write
            else self.session_provider.read_session(
                source=self.datasource, force_primary=force_primary
            )
        )
        async with scope as session:
            yield session

    async def insert(self, obj: T) -> T:
        async with self._get_session_scope(for_write=True) as session:
            session.add(obj)
            await session.flush()
            return obj

    async def insert_batch(self, objects: list[T], *, chunk_size: int = 500) -> list[T]:
        """分块 flush，但整批共用一次事务；任意块失败全部回滚。"""
        self._validate_chunk_size(chunk_size)
        if not objects:
            return objects
        async with self._get_session_scope(for_write=True) as session:
            for start in range(0, len(objects), chunk_size):
                session.add_all(objects[start : start + chunk_size])
                await session.flush()
            return objects

    @staticmethod
    def _validate_chunk_size(chunk_size):
        if type(chunk_size) is not int or chunk_size < 1:
            raise ValueError("chunk_size 必须为正整数")

    async def update_batch(
        self, rows: list[Mapping[str, object]], *, chunk_size: int = 500
    ) -> list[T]:
        """每行提供主键和业务字段；NULL 原样写入，缺失记录使整批回滚。

        返回对象与输入顺序一致；拒绝重复主键，避免一批内覆盖语义不明确。
        """
        self._validate_chunk_size(chunk_size)
        key = inspect(self.model).primary_key[0]
        allowed = set(inspect(self.model).column_attrs.keys()) - IMMUTABLE_FIELDS - {key.key}
        identifiers = []
        for row in rows:
            if not isinstance(row, Mapping) or row.get(key.key) is None:
                raise ValueError("批量更新每行必须包含非空主键")
            if set(row) - allowed - {key.key}:
                raise ValueError("更新包含未知字段或系统维护字段")
            identifiers.append(row[key.key])
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("批量更新不能包含重复主键")
        if not rows:
            return []
        changed = []
        async with self._get_session_scope(for_write=True) as session:
            for start in range(0, len(rows), chunk_size):
                chunk = rows[start : start + chunk_size]
                current = {
                    getattr(obj, key.key): obj
                    for obj in (
                        await session.scalars(
                            select(self.model)
                            .where(key.in_(identifiers[start : start + chunk_size]))
                            .order_by(key)
                            .with_for_update()
                        )
                    ).all()
                }
                if len(current) != len(chunk):
                    raise LookupError(f"{self.model.__name__} 批量更新包含不存在或已删除记录")
                for row in chunk:
                    obj = current[row[key.key]]
                    for name, value in row.items():
                        if name != key.key:
                            setattr(obj, name, value)
                    changed.append(obj)
                await session.flush()
            return changed

    async def upsert(
        self,
        values: Mapping[str, object],
        *,
        conflict_columns: Collection[str],
        update_columns: Collection[str],
    ) -> T:
        """原子插入或更新并返回持久化实体；冲突键必须为非空完整唯一键。

        只更新明确列，不更新主键/创建审计/冲突键，不复活软删除记录。
        其他唯一键冲突或已删除目标使事务失败。generated_ids 仅记录可确认
        插入成功的 Snowflake 候选；数据库 identity upsert 不推测插入分支。
        """
        if not issubclass(self.model, BaseDO) or not isinstance(values, Mapping):
            raise ValueError("upsert 要求 BaseDO 和字段 mapping")
        table = self.model.__table__
        conflicts, updates = tuple(conflict_columns), tuple(update_columns)
        allowed = set(inspect(self.model).column_attrs.keys())
        if set(values) - allowed or set(values) & (IMMUTABLE_FIELDS - {"id"}):
            raise ValueError("upsert 包含未知字段或系统维护字段")
        if (
            not conflicts
            or not updates
            or len(set(conflicts)) != len(conflicts)
            or len(set(updates)) != len(updates)
        ):
            raise ValueError("upsert 必须明确不重复的冲突键和更新列")
        unique_keys = {frozenset(column.key for column in table.primary_key)}
        unique_keys.update(
            frozenset(column.key for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        )
        unique_keys.update(
            frozenset(column.key for column in index.columns)
            for index in table.indexes
            if index.unique
            and not any(
                option.get("where") is not None for option in index.dialect_options.values()
            )
        )
        if frozenset(conflicts) not in unique_keys:
            raise ValueError("冲突列必须匹配模型声明的完整非部分唯一键")
        if any(name not in values or values[name] is None for name in conflicts):
            raise ValueError("冲突键必须显式提供非 NULL 值")
        if set(updates) - set(values) or set(updates) & (IMMUTABLE_FIELDS | set(conflicts)):
            raise ValueError("更新列须有输入值且不能包含系统字段或冲突键")
        statement = AtomicUpsert(table, conflicts, updates).values(dict(values))
        with self.session_provider.options(include_deleted=True):
            async with self._get_session_scope(for_write=True) as session:
                result = await session.execute(statement)
                current = await session.scalar(
                    select(self.model)
                    .where(*(table.c[name] == values[name] for name in conflicts))
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if current is None:
                    raise ValueError("upsert 命中了指定冲突键以外的唯一约束")
                if current.deleted:
                    raise ValueError("upsert 不允许覆盖或复活已软删除记录")
                execution = self.session_provider.context.current()
                if (
                    result.generated_id is not None
                    and current.id == result.generated_id
                    and execution is not None
                ):
                    execution.generated_ids.append(current.id)
                return current

    async def update_by_id(self, obj: T) -> T:
        """只更新已存在记录，不通过 merge 隐式新增缺失主键。"""
        primary_key = inspect(self.model).primary_key[0]
        source = inspect(obj)
        identifier = getattr(obj, primary_key.key)
        values = {
            column.key: source.dict[column.key]
            for column in inspect(self.model).column_attrs
            if column.key not in IMMUTABLE_FIELDS
            and column.key != primary_key.key
            and column.key in source.dict
        }
        async with self._get_session_scope(for_write=True) as session:
            if source.session is session.sync_session:
                session.expunge(obj)
            with session.no_autoflush:
                current = await session.scalar(
                    select(self.model).where(primary_key == identifier).with_for_update()
                )
            if current is None:
                raise LookupError(f"{self.model.__name__} 记录不存在")
            for field, value in values.items():
                setattr(current, field, value)
            await session.flush()
            return current

    async def update_by_condition(self, values: Mapping[str, object], *conditions) -> int:
        """显式字段映射允许写入 NULL；拒绝更新系统字段和无条件批量写入。"""
        if not conditions:
            raise ValueError("批量更新必须指定条件")
        allowed = (
            set(inspect(self.model).column_attrs.keys())
            - IMMUTABLE_FIELDS
            - {column.key for column in inspect(self.model).primary_key}
        )
        if set(values) - allowed:
            raise ValueError("更新包含未知字段或系统维护字段")
        if not values:
            return 0
        return (await self.write(update(self.model).where(*conditions).values(**values))).rowcount

    async def delete_by_id(self, identifier) -> int:
        return await self.soft_delete_by_condition(inspect(self.model).primary_key[0] == identifier)

    async def delete_by_ids(self, identifiers: Collection) -> int:
        if not identifiers:
            return 0
        return await self.soft_delete_by_condition(
            inspect(self.model).primary_key[0].in_(identifiers)
        )

    async def soft_delete_by_condition(self, *conditions) -> int:
        if not conditions or not issubclass(self.model, BaseDO):
            raise ValueError("逻辑删除要求 BaseDO 和明确条件")
        return (
            await self.write(update(self.model).where(*conditions).values(deleted=True))
        ).rowcount

    async def purge_by_id(self, identifier) -> int:
        return await self.purge_by_condition(inspect(self.model).primary_key[0] == identifier)

    async def purge_by_condition(self, *conditions) -> int:
        if not conditions:
            raise ValueError("物理清理必须指定条件")
        with self.session_provider.options(include_deleted=True):
            async with self._get_session_scope(for_write=True) as session:
                return (await session.execute(delete(self.model).where(*conditions))).rowcount

    async def purge_limited_by_condition(self, *conditions, limit: int) -> int:
        """先锁定有界主键集合再清理；MySQL 和 PostgreSQL 都遵守同一条数限制。"""
        if not conditions or type(limit) is not int or limit < 1:
            raise ValueError("限定清理要求明确条件和正整数 limit")
        key = inspect(self.model).primary_key[0]
        with self.session_provider.options(include_deleted=True):
            async with self._get_session_scope(for_write=True) as session:
                ids = list(
                    (
                        await session.scalars(
                            select(key)
                            .where(*conditions)
                            .order_by(key)
                            .limit(limit)
                            .with_for_update(skip_locked=True)
                        )
                    ).all()
                )
                if not ids:
                    return 0
                return (await session.execute(delete(self.model).where(key.in_(ids)))).rowcount

    async def select_by_id(self, identifier) -> T | None:
        key = inspect(self.model).primary_key[0]
        return (
            (await self.read(select(self.model).where(key == identifier))).scalars().one_or_none()
        )

    async def select_by_ids(self, identifiers: Collection) -> list[T]:
        if not identifiers:
            return []
        return list(
            (
                await self.read(
                    select(self.model).where(inspect(self.model).primary_key[0].in_(identifiers))
                )
            )
            .scalars()
            .all()
        )

    async def select_list(self, *conditions) -> list[T]:
        return list((await self.read(select(self.model).where(*conditions))).scalars().all())

    async def count(self, *conditions) -> int:
        return (
            await self.read(select(func.count()).select_from(self.model).where(*conditions))
        ).scalar_one()

    async def paginate_query(self, statement: Select, query: PageQuery | None = None, **ordering):
        ManagedSession.validate_statement(statement, readonly=True)
        async with self._get_session_scope() as session:
            return await self.paginator.paginate_query(session, statement, query, **ordering)

    async def read(self, statement):
        ManagedSession.validate_statement(statement, readonly=True)
        async with self._get_session_scope() as session:
            return await session.execute(statement)

    async def read_from_primary(self, statement):
        ManagedSession.validate_statement(statement, readonly=True)
        async with self._get_session_scope(force_primary=True) as session:
            return await session.execute(statement)

    async def write(self, statement, params=None):
        if not isinstance(statement, (Insert, Update)):
            raise ValueError("write 只接受 INSERT/UPDATE；物理删除使用 purge")
        async with self._get_session_scope(for_write=True) as session:
            return await session.execute(statement, params)

    async def execute(self, statement, params=None):
        if isinstance(statement, (Insert, Update)):
            return await self.write(statement, params)
        if not isinstance(statement, Select) or not self._automatic_select(statement):
            raise ValueError("复杂查询使用显式 read/read_from_primary，物理删除使用 purge")
        for_write = statement._for_update_arg is not None or any(
            isinstance(element, (Insert, Update, Delete)) for element in visitors.iterate(statement)
        )
        async with self._get_session_scope(for_write=for_write) as session:
            return await session.execute(statement, params)

    @staticmethod
    def _automatic_select(statement):
        sources = statement.get_final_froms()
        return (
            all(
                description.get("entity") is not None
                for description in statement.column_descriptions
            )
            and len(sources) == 1
            and isinstance(sources[0], Table)
            and not any(
                element is not statement and isinstance(element, SelectBase)
                for element in visitors.iterate(statement)
            )
        )
