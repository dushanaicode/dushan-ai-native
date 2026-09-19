from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import (
    Delete,
    Insert,
    Table,
    UniqueConstraint,
    Update,
    and_,
    bindparam,
    event,
    inspect,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import BindParameter, ClauseElement
from sqlalchemy.util import immutabledict

from framework.starter_database.definitions.constants.row_access_error_codes import (
    RowAccessErrorCodes,
)
from framework.starter_database.model.model_policy import ModelPolicy
from framework.starter_database.query.combined_condition_builder import CombinedConditionBuilder
from framework.starter_database.query.dml_read_sources import DmlReadSources
from framework.starter_database.query.row_access_registry import RowAccessRegistry
from framework.starter_database.repository.atomic_upsert import AtomicUpsert
from framework.starter_database.spi.session_policy import SessionPolicy


class RowAccessPolicy(SessionPolicy):
    """同一 Session 的租户和记录范围先组合，再统一校验 SQL 与写入结果。"""

    def __init__(self, rules):
        self.rules = rules
        self.registry = RowAccessRegistry(rules)
        self.builder = CombinedConditionBuilder(self.registry, rules)
        self._internal = ContextVar(f"row_access_preflight_{id(self)}", default=False)

    def failure(self, reason):
        return self.rules[0].failure(reason)

    def check(self, session):
        for rule, previous in session._row_access_keys.items():
            if previous != rule.scope_key():
                raise rule.failure(RowAccessErrorCodes.STALE)

    def _bind_scope(self, session, configs):
        for rule in self.rules:
            if any(
                not rule.registry.require(config.table).public
                or rule.registry.require(config.table).tenant_column is not None
                for config in configs
            ):
                if rule not in session._row_access_keys:
                    session._row_access_keys[rule] = rule.scope_key()
        self.check(session)

    def _prepare_row(self, config, row):
        for rule in self.rules:
            rule.prepare_insert(rule.registry.require(config.table), row)

    def _validate_row(self, config, row, operation):
        for rule in self.rules:
            rule.validate_row(rule.registry.require(config.table), row, operation)

    def bind(self, session):
        session._row_access_keys = {}
        event.listen(session, "do_orm_execute", self.before_execute, retval=True)
        event.listen(session, "before_flush", self.before_flush)
        event.listen(session, "after_attach", self.after_attach)

    def after_attach(self, session, instance):
        config = self.registry.require_mapper(inspect(instance).mapper)
        self._bind_scope(session, (config,))

    @contextmanager
    def _preflight(self, session):
        token = self._internal.set(True)
        try:
            with session.no_autoflush:
                yield
        finally:
            self._internal.reset(token)

    def before_execute(self, state):
        if self._internal.get():
            return None
        statement = state.statement
        self._validate_parameters(statement, state.parameters)
        tables = self.registry.validate_statement(statement)
        configs = [self.registry.require(table) for table in tables]
        self._bind_scope(state.session, configs)
        if state.is_select:
            state.statement = self.builder.select(statement)
            if state.is_column_load and state.bind_mapper is not None:
                config = self.registry.require_mapper(state.bind_mapper)
                state.statement = state.statement.where(self.builder.condition(config, "select"))
            return None
        if not isinstance(statement, (Insert, Update, Delete)) or not isinstance(
            statement.table, Table
        ):
            raise self.failure(RowAccessErrorCodes.CONFIGURATION)
        if (
            isinstance(statement, (Update, Delete))
            and state.session.autoflush
            and state.execution_options.get("autoflush", True)
        ):
            state.session.flush()
        statement = self._subqueries(statement)
        if isinstance(statement, (Update, Delete)):
            # 子查询内部由 builder 处理；裸 FROM/USING 表同样受读取范围约束。
            statement = DmlReadSources.filter(statement, self.registry, self.builder)
        if isinstance(statement, (Insert, Update)) and statement._values is not None:
            statement._values = immutabledict(statement._values)
        state.statement = statement
        config = self.registry.require(statement.table)
        if config.public and config.tenant_column is None:
            if isinstance(statement, Delete):
                with self._preflight(state.session):
                    state.session.execute(
                        select(*config.table.primary_key)
                        .where(*statement._where_criteria)
                        .with_for_update(),
                        state.parameters,
                    ).all()
                self._cascades(state.session, config, and_(true(), *statement._where_criteria))
            return None
        if isinstance(statement, Insert):
            return self._insert(state, config)

        operation = "update" if isinstance(statement, Update) else "delete"
        if isinstance(statement, Update):
            columns = {getattr(key, "key", key) for key in (statement._values or {})}
            columns.update(getattr(key, "key", key) for key, _ in (statement._ordered_values or ()))
            columns.update(state.parameters or {})
            forbidden = {
                *config.authority_columns,
                *(column.key for column in config.table.primary_key),
            }
            if columns & forbidden:
                raise self.failure(RowAccessErrorCodes.WRITE)
        condition = self.builder.condition(config, operation)
        with self._preflight(state.session):
            business = and_(true(), *statement._where_criteria)
            identifiers = state.session.execute(
                select(*config.table.primary_key).where(business).with_for_update(),
                state.parameters,
            ).all()
            target = tuple_(*config.table.primary_key).in_(
                bindparam(
                    "_dushan_dp_targets",
                    [tuple(row) for row in identifiers],
                    expanding=True,
                    unique=True,
                )
            )
            denied = (
                select(1)
                .select_from(config.table)
                .where(target, condition.is_not(true()))
                .limit(1)
                .with_for_update()
            )
            if state.session.scalar(denied) is not None:
                raise self.failure(RowAccessErrorCodes.WRITE)
        if isinstance(statement, Delete):
            self._cascades(state.session, config, target)
        state.statement = statement.where(target, condition)
        # ORM synchronize_session 的内部 SELECT 使用已经过滤并锁定的目标集合；
        # 它不是新的业务读取，不额外要求工作负载拥有 select 权限。
        token = self._internal.set(True)
        try:
            return state.invoke_statement()
        finally:
            self._internal.reset(token)

    def _validate_parameters(self, statement, parameters):
        if parameters is None:
            return
        declared = {
            node.key
            for node in visitors.iterate(statement)
            if isinstance(node, BindParameter) and not node.unique
        }
        if any(name.startswith(("_dushan_dp_", "_dushan_tenant_")) for name in declared):
            raise self.failure(RowAccessErrorCodes.CONFIGURATION)
        if isinstance(statement, (Insert, Update)):
            declared.update(statement.table.c.keys())
        rows = parameters if isinstance(parameters, (list, tuple)) else (parameters,)
        if any(set(row) - declared for row in rows):
            raise self.failure(RowAccessErrorCodes.CONFIGURATION)

    def _subqueries(self, expression):
        return self.builder.expression(expression)

    def _cascades(self, session, parent, targets, visited=frozenset()):
        """数据库 FK 级联也必须逐层授权，不能由合法父记录删除隐藏子记录。"""
        if parent.table.key in visited:
            raise self.failure(RowAccessErrorCodes.CONFIGURATION)
        for table in parent.table.metadata.tables.values():
            for constraint in table.foreign_key_constraints:
                action = (constraint.ondelete or "").upper()
                if constraint.referred_table is not parent.table or action not in {
                    "CASCADE",
                    "SET NULL",
                    "SET DEFAULT",
                }:
                    continue
                child = self.registry.require(table)
                self._bind_scope(session, (child,))
                elements = tuple(constraint.elements)
                condition = tuple_(*(item.parent for item in elements)).in_(
                    select(*(item.column for item in elements)).where(targets)
                )
                operation = "delete" if action == "CASCADE" else "update"
                permission = self.builder.condition(child, operation)
                if operation == "update" and set(constraint.column_keys) & set(
                    child.authority_columns
                ):
                    permission = ~true()
                with self._preflight(session):
                    affected = session.execute(
                        select(*table.primary_key).where(condition).with_for_update()
                    ).all()
                    if (
                        session.scalar(
                            select(1)
                            .select_from(table)
                            .where(condition, permission.is_not(true()))
                            .limit(1)
                            .with_for_update()
                        )
                        is not None
                    ):
                        raise self.failure(RowAccessErrorCodes.WRITE)
                if affected and action == "CASCADE":
                    self._cascades(session, child, condition, visited | {parent.table.key})

    def _insert(self, state, config):
        statement = state.statement
        rows = ModelPolicy._insert_rows(statement, state.parameters)
        if not rows:
            raise self.failure(RowAccessErrorCodes.WRITE)
        for row in rows:
            self._prepare_row(config, row)
            self._validate_row(config, row, "insert")
        statement = statement._generate()
        statement._values, statement._multi_values = None, ()
        state.statement = statement
        state.parameters = rows[0] if len(rows) == 1 else rows
        if not isinstance(statement, AtomicUpsert):
            return None
        if len(rows) != 1 or set(statement.update_columns) & set(config.authority_columns):
            raise self.failure(RowAccessErrorCodes.WRITE)
        row = rows[0]
        self._check_conflicts(state.session, config, row)
        secured = statement._generate()
        secured.access_condition = and_(
            statement.access_condition if statement.access_condition is not None else true(),
            self.builder.condition(config, "update"),
        )
        state.statement = secured
        result = state.invoke_statement()
        # 方言可能把冲突更新变成 no-op，必须明确验证目标而不是声称成功。
        matches = and_(*(config.table.c[name] == row[name] for name in statement.conflict_columns))
        with self._preflight(state.session):
            target = state.session.scalar(
                select(1)
                .select_from(config.table)
                .where(matches, secured.access_condition)
                .with_for_update()
            )
        if target is None:
            raise self.failure(RowAccessErrorCodes.WRITE)
        return result

    def _check_conflicts(self, session, config, row):
        table = config.table
        keys = [tuple(table.primary_key.columns)]
        keys.extend(
            tuple(item.columns) for item in table.constraints if isinstance(item, UniqueConstraint)
        )
        keys.extend(tuple(item.columns) for item in table.indexes if item.unique)
        conditions = []
        for key in keys:
            if all(column.key in row and row[column.key] is not None for column in key):
                conditions.append(and_(*(column == row[column.key] for column in key)))
        if not conditions:
            raise self.failure(RowAccessErrorCodes.CONFIGURATION)
        conflict = or_(*conditions)
        allowed = self.builder.condition(config, "update")
        with self._preflight(session):
            if (
                session.scalar(
                    select(1)
                    .select_from(table)
                    .where(conflict, allowed.is_not(true()))
                    .limit(1)
                    .with_for_update()
                )
                is not None
            ):
                raise self.failure(RowAccessErrorCodes.WRITE)
            session.execute(select(*table.primary_key).where(conflict).with_for_update()).all()

    def before_flush(self, session, flush_context, instances):
        existing = defaultdict(list)
        for operation, objects in (
            ("insert", session.new),
            ("update", session.dirty),
            ("delete", session.deleted),
        ):
            for obj in objects:
                if operation == "update" and not session.is_modified(
                    obj, include_collections=False
                ):
                    continue
                state = inspect(obj)
                config = self.registry.require_mapper(state.mapper)
                self._bind_scope(session, (config,))
                attributes = {
                    column.key: state.mapper.get_property_by_column(column).key
                    for column in config.table.columns
                }
                for attribute in attributes.values():
                    value = state.dict.get(attribute)
                    if isinstance(value, ClauseElement):
                        self.registry.validate_statement(value)
                        setattr(obj, attribute, self._subqueries(value))
                if config.public and config.tenant_column is None:
                    continue
                if operation == "insert":
                    row = {
                        column: state.dict[attr]
                        for column, attr in attributes.items()
                        if attr in state.dict
                    }
                    self._prepare_row(config, row)
                    self._validate_row(config, row, operation)
                    for column, value in row.items():
                        setattr(obj, attributes[column], value)
                    continue
                immutable = (
                    *config.authority_columns,
                    *(column.key for column in config.table.primary_key),
                )
                if any(state.attrs[attributes[name]].history.has_changes() for name in immutable):
                    raise self.failure(RowAccessErrorCodes.WRITE)
                existing[(config.table.key, operation)].append(state.identity)
        for (key, operation), identifiers in existing.items():
            config = self.registry.entries[key]
            primary_keys = tuple(config.table.primary_key.columns)
            target = tuple_(*primary_keys).in_(identifiers)
            with self._preflight(session):
                result = session.execute(
                    select(*primary_keys)
                    .where(target, self.builder.condition(config, operation))
                    .with_for_update()
                ).all()
            if len(result) != len(set(identifiers)):
                raise self.failure(RowAccessErrorCodes.WRITE)
            if operation == "delete":
                self._cascades(session, config, target)
