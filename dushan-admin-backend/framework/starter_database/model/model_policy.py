import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import Delete, Insert, Update, event, false
from sqlalchemy.orm import LoaderCriteriaOption, with_loader_criteria
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import BindParameter

from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.context.database_context import DatabaseContext
from framework.starter_database.id.snowflake_utils import SnowflakeUtils
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.repository.atomic_upsert import AtomicUpsert
from framework.starter_database.session.write_result import WriteResult


class ModelPolicy:
    """仅绑定当前应用创建的 Session，统一 ORM/Core ID、UTC 审计和软删除。"""

    def __init__(self, settings: DatabaseSettings, context: DatabaseContext) -> None:
        self.settings, self.context = settings, context
        self.account_provider = None
        self.session_policies = []
        self.ids = (
            SnowflakeUtils(settings.snowflake_machine_id)
            if settings.enabled and settings.id_strategy == "snowflake"
            else None
        )

    def bind(self, session) -> None:
        session.access_policies = tuple(self.session_policies)
        # 行级策略要验证最终主键和审计值，先补齐框架负责生成的字段。
        event.listen(session, "before_flush", self.before_flush)
        for policy in session.access_policies:
            policy.bind(session)
        event.listen(session, "after_flush", self.after_flush)
        event.listen(session, "do_orm_execute", self.before_execute, retval=True)

    def execution(self, session):
        return (
            self.context.current() if asyncio.current_task() is session.owner else session.execution
        )

    def prepare_statement(self, statement, session):
        """先确定 Database 自身的写入边界，再由上层 Session 策略验证目标集合。"""
        execution = self.execution(session)
        if (
            self.settings.soft_delete_enabled
            and not (execution is not None and execution.include_deleted)
            and isinstance(statement, (Update, Delete))
            and "deleted" in statement.table.c
        ):
            return statement.where(statement.table.c.deleted == false())
        return statement

    def audit_values(self, session, *, inserting=False):
        execution = self.execution(session)
        account = (
            None if execution is None or not self.settings.audit_enabled else execution.account_id
        )
        if self.settings.audit_enabled and account is None and self.account_provider is not None:
            account = self.account_provider.get_current_account_id()
        values = {"update_time": datetime.now(UTC).replace(tzinfo=None)}
        if account is not None:
            values["updater"] = account
        if inserting:
            values["create_time"] = values["update_time"]
            if account is not None:
                values["creator"] = account
        return values

    def before_flush(self, session, flush_context, instances) -> None:
        values = self.audit_values(session, inserting=True)
        session._generated_database_ids = []
        for obj in session.new:
            if isinstance(obj, BaseDO):
                if obj.id is None:
                    if self.ids is not None:
                        obj.id = self.ids.get_id()
                    session._generated_database_ids.append(obj)
                for name, value in values.items():
                    setattr(obj, name, value)
        for obj in session.dirty:
            if isinstance(obj, BaseDO) and session.is_modified(obj, include_collections=False):
                obj.update_time = values["update_time"]
                if "updater" in values:
                    obj.updater = values["updater"]

    def after_flush(self, session, flush_context) -> None:
        execution = self.execution(session)
        if execution is not None:
            execution.generated_ids.extend(
                obj.id for obj in session._generated_database_ids if obj.id is not None
            )
        session._generated_database_ids = []

    @staticmethod
    def _insert_rows(statement, parameters):
        if statement.select is not None:
            raise ValueError("受管 INSERT 不接受 SELECT 来源；请分块提供明确行值")
        if statement._post_values_clause is not None and not isinstance(statement, AtomicUpsert):
            raise ValueError("冲突写入请使用 mapper.upsert，以保证审计与软删除策略")
        base = {getattr(key, "key", key): value for key, value in (statement._values or {}).items()}
        if statement._multi_values:
            if parameters is not None:
                raise ValueError("多 values INSERT 不能再混用 execute 参数")
            raw_rows = [row for group in statement._multi_values for row in group]
        elif parameters is None:
            raw_rows = [{}]
        else:
            raw_rows = [parameters] if isinstance(parameters, Mapping) else parameters
        rows = []
        for raw in raw_rows:
            if not isinstance(raw, Mapping):
                raise ValueError("INSERT 行必须使用字段 mapping")
            supplied = {getattr(key, "key", key): value for key, value in raw.items()}

            def resolve(element):
                if isinstance(element, LoaderCriteriaOption):
                    return element
                if isinstance(element, BindParameter):
                    if element.key in supplied:
                        return BindParameter(element.key, supplied[element.key], type_=element.type)
                    if element.required:
                        raise ValueError(f"INSERT 缺少绑定参数 {element.key}")
                return None

            row = {
                key: visitors.replacement_traverse(value, {}, resolve)
                if hasattr(value, "_compiler_dispatch")
                else value
                for key, value in base.items()
            }
            row.update({key: value for key, value in supplied.items() if key in statement.table.c})
            for key, value in tuple(row.items()):
                if isinstance(value, BindParameter) and not value.required:
                    row[key] = value.value
            rows.append(row)
        return rows

    def insert(self, state):
        statement = state.statement
        rows = self._insert_rows(statement, state.parameters)
        if not rows:
            raise ValueError("INSERT 参数集合不能为空")
        audit = self.audit_values(state.session, inserting=True)
        generated = []
        for row in rows:
            row.update(audit)
            row.setdefault("creator", "")
            row.setdefault("updater", "")
            row.setdefault("deleted", False)
            missing = row.get("id") is None
            if missing:
                row.pop("id", None)
                if self.ids is not None:
                    row["id"] = self.ids.get_id()
            generated.append(missing)
        base = statement._generate()
        base._values = None
        base._multi_values = ()
        state.parameters = None
        if isinstance(statement, AtomicUpsert):
            if len(rows) != 1:
                raise ValueError("upsert 仅接受单行；多次调用可复用外层事务")
            base.audit_update_columns = (
                ("update_time", "updater") if "updater" in audit else ("update_time",)
            )
            result = state.invoke_statement(
                base.values(rows[0]), execution_options={"dml_strategy": "raw"}
            )
            metadata = result._metadata
            rowcount = result.rowcount
            result.close()
            return WriteResult(
                metadata,
                [],
                rowcount=rowcount,
                primary_keys=[],
                generated_id=rows[0].get("id") if generated[0] else None,
            )
        dialect = state.session.get_bind().dialect
        needs_identity = any(
            flag and "id" not in row for flag, row in zip(generated, rows, strict=True)
        )
        # RETURNING 方言和已有主键保留真批量；仅无返回能力的 identity 路径逐行取 lastrowid。
        same_shape = all(row.keys() == rows[0].keys() for row in rows)
        returning_rows = dialect.insert_returning and dialect.name != "dm"
        batch = same_shape and (not needs_identity or returning_rows)
        groups = [rows] if batch else [[row] for row in rows]
        all_rows, keys, identifiers = [], [], []
        total = 0
        for group in groups:
            executemany = len(group) > 1 and not dialect.supports_multivalues_insert
            current = base if executemany else base.values(group if len(group) > 1 else group[0])
            collect_returning = needs_identity and dialect.insert_returning
            original_returning = bool(current._returning)
            if collect_returning:
                current = current.returning(statement.table.c.id.label(None))
            state.parameters = group if executemany else None
            strategy = "orm" if original_returning and state.is_orm_statement else "raw"
            result = state.invoke_statement(current, execution_options={"dml_strategy": strategy})
            state.parameters = None
            total += len(group)
            returned = result.fetchall() if original_returning or collect_returning else []
            metadata = result._metadata
            if collect_returning:
                group_ids = [row[-1] for row in returned]
                if original_returning:
                    metadata = result.columns(*range(len(result.keys()) - 1))._metadata
                    all_rows.extend(tuple(row[:-1]) for row in returned)
            else:
                group_ids = [row.get("id") for row in group]
                if len(group) == 1 and group_ids[0] is None:
                    group_ids[0] = result.inserted_primary_key[0]
                all_rows.extend(returned)
            identifiers.extend(group_ids)
            keys.extend((identifier,) for identifier in group_ids)
            result.close()
        execution = self.execution(state.session)
        if execution is not None:
            execution.generated_ids.extend(
                identifier
                for flag, identifier in zip(generated, identifiers, strict=True)
                if flag and identifier is not None
            )
        return WriteResult(
            metadata,
            all_rows,
            rowcount=total,
            primary_keys=keys,
            returns_rows=bool(statement._returning),
        )

    def before_execute(self, state):
        execution = self.execution(state.session)
        include_deleted = execution is not None and execution.include_deleted
        statement = state.statement
        if isinstance(statement, Insert) and all(
            name in statement.table.c
            for name in ("id", "creator", "create_time", "updater", "update_time", "deleted")
        ):
            return self.insert(state)
        if self.settings.soft_delete_enabled and not include_deleted:
            if state.is_select and not state.is_column_load:
                state.statement = statement.options(
                    with_loader_criteria(
                        BaseDO, lambda model: model.deleted == false(), include_aliases=True
                    )
                )
        if isinstance(statement, Update) and "update_time" in statement.table.c:
            supplied = {getattr(key, "key", key) for key in (statement._values or {})}
            supplied.update(state.parameters or {})
            if supplied & {"id", "creator", "create_time", "tenant_id"}:
                raise ValueError("Core UPDATE 不能修改主键或创建审计字段")
            if state.parameters and set(state.parameters) & {"updater", "update_time", "deleted"}:
                raise ValueError("系统维护字段不能通过 execute 参数覆盖")
            state.statement = state.statement.values(**self.audit_values(state.session))
        return None
