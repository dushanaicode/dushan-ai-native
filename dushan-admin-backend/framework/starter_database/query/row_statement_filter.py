from abc import ABC, abstractmethod

from sqlalchemy import Column, Table, inspect, select
from sqlalchemy.orm import QueryableAttribute, with_expression, with_loader_criteria
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import Label
from sqlalchemy.sql.selectable import CTE, Alias, Select, Subquery


class RowStatementFilter(ABC):
    """受管行策略共用的 ORM/Core 重写机制，不查询身份或创建数据库资源。

    registry 负责核验表来源，声明包含 table/model/public/tenant_column；
    condition 由租户或数据权限策略实现。全局公开声明不要求执行上下文。
    """

    def __init__(self, registry, invalid):
        self.registry = registry
        self._invalid = invalid

    @abstractmethod
    def condition(self, config, operation, *, orm=False, entity=None):
        """为经过登记的表返回当前执行允许的行条件。

        entity 为 None 时绑定到声明的原模型；传入某个 aliased() 别名对象时，
        条件必须改用该别名的列，不能重复套用原模型的条件（否则不会真正约束别名）。
        """
        ...

    @staticmethod
    def _column(config, name, orm, entity=None):
        if not orm:
            return config.table.c[name]
        mapper = inspect(config.model)
        key = mapper.get_property_by_column(config.table.c[name]).key
        return getattr(entity if entity is not None else config.model, key)

    def select(
        self,
        statement,
        *,
        orm=True,
        outer_tables=frozenset(),
        outer_selectables=frozenset(),
        outer_replacements=None,
    ):
        referenced = self.registry.validate_statement(statement)
        if all(
            self.registry.require(table).public
            and self.registry.require(table).tenant_column is None
            for table in referenced
        ):
            return statement
        nodes = tuple(visitors.iterate(statement))
        has_orm = any(
            isinstance(node, Select) and node._propagate_attrs.get("compile_state_plugin") == "orm"
            for node in nodes
        )
        if has_orm and any(isinstance(node, CTE) and node.recursive for node in nodes):
            raise self._invalid()
        orm_tables, orm_aliases, core_aliases, orm_selectables = (
            self._orm_entities(statement, outer_selectables) if orm else (set(), {}, {}, set())
        )
        # 相关子查询必须引用外层同一个受限来源，重新创建副本会丢失关联。
        replacements = {
            table: source
            for table, source in ({} if outer_replacements is None else outer_replacements).items()
            if table not in orm_tables
        }
        alias_replacements = {}
        options = []
        direct_conditions = []
        locked_tables = (
            {
                source._deannotate()
                for source in statement.get_final_froms()
                if isinstance(source, Table)
            }
            if isinstance(statement, Select) and statement._for_update_arg is not None
            else set()
        )
        for config in self.registry.entries.values():
            if config.table not in referenced:
                continue
            if config.public and config.tenant_column is None:
                continue
            condition = self.condition(config, "select")
            if config.table in locked_tables and config.table not in orm_tables:
                direct_conditions.append(condition)
            elif (
                config.table not in orm_tables
                and config.table not in outer_tables
                and config.table not in replacements
            ):
                restricted = select(config.table).where(condition)
                if isinstance(statement, Select) and statement._for_update_arg is not None:
                    restricted = restricted._generate()
                    restricted._for_update_arg = statement._for_update_arg
                replacements[config.table] = restricted.subquery()
            for alias_node in core_aliases.get(config.table, ()):
                # 本层别名是独立读取来源，不因外层关联了同一物理表而免于过滤。
                alias_replacements[alias_node] = (
                    select(config.table).where(condition).alias(alias_node.name)
                )
            if (
                orm
                and config.model is not None
                and statement._propagate_attrs.get("compile_state_plugin") == "orm"
            ):
                options.append(
                    with_loader_criteria(
                        config.model,
                        self.condition(config, "select", orm=True),
                        propagate_to_loaders=True,
                    )
                )
                for alias_entity in orm_aliases.get(config.table, ()):
                    # 嵌套 SELECT 的 options 不一定参与外层 ORM 编译，别名条件
                    # 必须同时登记到本层编译入口，且直接绑定对应别名的列。
                    options.append(
                        with_loader_criteria(
                            alias_entity,
                            self.condition(config, "select", orm=True, entity=alias_entity),
                            propagate_to_loaders=True,
                        )
                    )
        if orm and isinstance(statement, Select):
            for projected in statement._raw_columns:
                inspected = projected._annotations.get("parententity")
                if inspected is None or not isinstance(projected, (Table, Alias, Subquery)):
                    continue
                mapper = inspected.mapper if inspected.is_aliased_class else inspected
                entity = inspected.entity if inspected.is_aliased_class else mapper.class_
                for prop in mapper.column_attrs:
                    if any(isinstance(node, Select) for node in visitors.iterate(prop.expression)):
                        options.append(
                            with_expression(
                                getattr(entity, prop.key),
                                self.expression(prop.expression, outer_tables={mapper.local_table}),
                            )
                        )

        def replace(node):
            if isinstance(node, Alias) and node._deannotate() in orm_selectables:
                # 投影列持有原 ORM 别名。改写其内部 Table 会克隆出另一个 JOIN
                # 目标；还需保留隐式 FROM 中不带标注的同一 selectable。
                return node
            if (
                isinstance(node, Label)
                and node._annotations.get("parententity") is not None
                and any(isinstance(child, Select) for child in visitors.iterate(node))
            ):
                return self.expression(
                    node._deannotate(), outer_tables=outer_tables | orm_tables
                ).label(node._annotations["proxy_key"])
            if orm and isinstance(node, Subquery) and self._orm_subquery(node.element):
                # relationship 的 JOIN 属性持有原别名；纯 ORM 子查询由顶层
                # loader criteria 过滤，保持引用才能避免同名别名出现两次。
                return node
            if isinstance(node, Select) and node is not statement:
                return self.select(
                    node,
                    orm=orm,
                    outer_tables=outer_tables | orm_tables,
                    outer_selectables=orm_selectables,
                    outer_replacements=replacements,
                )
            if isinstance(node, Alias) and node in alias_replacements:
                return alias_replacements[node]
            # 携带 parententity 标注的节点是真实的 ORM 实体引用（未别名或别名），已交给
            # with_loader_criteria 处理；替换成受限子查询会破坏实体身份映射。
            if (
                isinstance(node, Table)
                and node in replacements
                and node._annotations.get("parententity") is None
            ):
                return replacements[node]
            if isinstance(node, Column) and node._annotations.get("parententity") is None:
                if node.table in replacements:
                    return replacements[node.table].c[node.key]
                if node.table in alias_replacements:
                    return alias_replacements[node.table].c[node.key]
            return None

        result = visitors.replacement_traverse(
            statement, {"stop_on": statement._with_options}, replace
        ).options(*options)
        return result.where(*direct_conditions) if direct_conditions else result

    def expression(self, expression, *, outer_tables=frozenset()):
        """嵌入 DML/映射属性的 SQL 不依赖外层 ORM options 才能过滤。"""
        return visitors.replacement_traverse(
            expression,
            {},
            lambda node: (
                self.select(node, orm=False, outer_tables=outer_tables)
                if isinstance(node, Select)
                else None
            ),
        )

    def _orm_entities(self, statement, outer_selectables=frozenset()):
        """局部 FROM 决定来源替换；所有嵌套 ORM 别名都向当前编译入口登记条件。"""
        orm_tables = set()
        orm_aliases = {}
        core_aliases = {}
        orm_selectables = set(outer_selectables)
        seen_aliases = set()
        for node in visitors.iterate(statement):
            entity = node._annotations.get("parententity")
            if entity is not None and entity.is_aliased_class and id(entity) not in seen_aliases:
                seen_aliases.add(id(entity))
                orm_aliases.setdefault(entity.mapper.local_table, []).append(entity.entity)
        # WHERE 中的普通 ORM 属性不能让整个物理表免于 Core 来源替换。
        pending = (
            [*statement._raw_columns, *statement._from_obj] if isinstance(statement, Select) else []
        )
        if isinstance(statement, Select):
            pending.extend(join[0] for join in statement._setup_joins)
        seen = set()
        while pending:
            node = pending.pop()
            if isinstance(node, QueryableAttribute):
                node = node.__clause_element__()
            if id(node) in seen:
                continue
            seen.add(id(node))
            if isinstance(node, Select):
                continue
            entity = node._annotations.get("parententity")
            if entity is not None and isinstance(node, (Column, Table, Alias)):
                if entity.is_aliased_class:
                    orm_selectables.add(entity.selectable)
                elif isinstance(node, (Column, Table)):
                    orm_tables.add(entity.local_table)
            pending.extend(node.get_children())
        # 只有谓词引用的 ORM 属性不足以登记 ORM FROM；对应隐式别名仍按
        # Core 来源过滤。外层已登记的别名保留原对象，以维持相关子查询关系。
        pending, seen = [statement], set()
        while pending:
            node = pending.pop()
            if id(node) in seen or isinstance(node, Select) and node is not statement:
                continue
            seen.add(id(node))
            entity = node._annotations.get("parententity")
            source = entity.selectable if entity is not None and entity.is_aliased_class else node
            if isinstance(source, Alias) and source._deannotate() not in orm_selectables:
                table = source.element
                if isinstance(table, Table):
                    target = self.registry.entries.get(table.key)
                    if target is not None and table._deannotate() is target.table:
                        aliases = core_aliases.setdefault(target.table, [])
                        if source not in aliases:
                            aliases.append(source)
            pending.extend(node.get_children())
        return orm_tables, orm_aliases, core_aliases, orm_selectables

    def _orm_tables(self, statement):
        return self._orm_entities(statement)[0]

    def _orm_subquery(self, statement):
        if not isinstance(statement, Select):
            return False
        owned = self._orm_tables(statement)
        if not owned or not self.registry.validate_statement(statement) <= owned:
            return False
        if any(isinstance(node, Alias) for node in visitors.iterate(statement)):
            return False
        nested = {
            node
            for expression in (statement, *statement.selected_columns)
            for node in visitors.iterate(expression)
            if isinstance(node, Select) and node is not statement
        }
        return all(self._orm_subquery(node) for node in nested)
