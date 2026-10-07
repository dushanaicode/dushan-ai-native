from itertools import product
from uuid import uuid4

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    Identity,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import registry
from sqlalchemy.schema import CreateTable

from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.model.base import Base
from module_infra.dal.dataobject.data_source.data_source_config_do import DataSourceConfigDO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_system.dal.dataobject.dept.post_do import PostDO


class TestGeneratedColumns:
    async def test_orm_inserts_computed_columns_with_generated_and_explicit_ids(
        self, database_settings
    ):
        """ORM 写入虚拟列模型时保留自增和显式 ID，不请求 DM 不支持的返回项。"""
        table = Table(
            "computed_inserts_" + uuid4().hex[:16],
            MetaData(),
            Column("id", Integer, Identity(), primary_key=True),
            Column("deleted", Boolean, nullable=False),
            Column(
                "active_key", SmallInteger, Computed(PostDO.__table__.c.active_key.computed.sqltext)
            ),
        )
        model = type("ComputedInsert", (), {})
        registry().map_imperatively(model, table)
        engine = create_async_engine(database_settings.sources[0].url.get_secret_value())
        created = False
        try:
            async with engine.begin() as connection:
                await connection.run_sync(table.create)
            created = True
            async with AsyncSession(engine) as session, session.begin():
                rows = [model(deleted=False), model(deleted=True), model(id=7000001, deleted=False)]
                session.add_all(rows)
                await session.flush()
                assert rows[0].id is not None and rows[1].id is not None
                assert len({row.id for row in rows}) == 3
                assert rows[2].id == 7000001
                assert (
                    await session.scalars(select(table.c.active_key).order_by(table.c.id))
                ).all() == [1, None, 1]
        finally:
            try:
                if created:
                    async with engine.begin() as connection:
                        await connection.run_sync(table.drop)
            finally:
                await engine.dispose()

    async def test_runtime_generated_flags_and_soft_delete_unique_key(self, database_settings):
        """真实实例计算三种有效标记，并允许软删除后复用唯一业务键。"""
        table = Table(
            "generated_flags_" + uuid4().hex[:16],
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("code", String(32), nullable=True),
            Column("deleted", Boolean, nullable=False),
            Column("master", Boolean, nullable=False),
            Column("is_default", Boolean, nullable=False),
            Column(
                "active_key", SmallInteger, Computed(PostDO.__table__.c.active_key.computed.sqltext)
            ),
            Column(
                "master_active",
                SmallInteger,
                Computed(FileConfigDO.__table__.c.master_active.computed.sqltext),
            ),
            Column(
                "default_active",
                SmallInteger,
                Computed(DataSourceConfigDO.__table__.c.default_active.computed.sqltext),
            ),
            UniqueConstraint("code", "active_key"),
        )
        engine = create_async_engine(database_settings.sources[0].url.get_secret_value())
        created = False
        try:
            async with engine.begin() as connection:
                await connection.run_sync(table.create)
            created = True
            async with engine.begin() as connection:
                for identifier, (deleted, master, is_default) in enumerate(
                    product((False, True), repeat=3), 1
                ):
                    await connection.execute(
                        insert(table).values(
                            id=identifier,
                            code=str(identifier),
                            deleted=deleted,
                            master=master,
                            is_default=is_default,
                        )
                    )
                    keys = (
                        await connection.execute(
                            select(
                                table.c.active_key, table.c.master_active, table.c.default_active
                            ).where(table.c.id == identifier)
                        )
                    ).one()
                    assert keys == (
                        None if deleted else 1,
                        1 if not deleted and master else None,
                        1 if not deleted and is_default else None,
                    )
                await connection.execute(
                    insert(table),
                    [
                        dict(id=20, code="same", deleted=False, master=False, is_default=False),
                        dict(id=21, code="same", deleted=True, master=False, is_default=False),
                        dict(id=22, code="same", deleted=True, master=False, is_default=False),
                        dict(id=24, code=None, deleted=False, master=False, is_default=False),
                        dict(id=25, code=None, deleted=False, master=False, is_default=False),
                    ],
                )
            with pytest.raises(IntegrityError):
                async with engine.begin() as connection:
                    await connection.execute(
                        insert(table).values(
                            id=23, code="same", deleted=False, master=False, is_default=False
                        )
                    )
            async with engine.begin() as connection:
                await connection.execute(update(table).where(table.c.id == 20).values(deleted=True))
                await connection.execute(
                    insert(table).values(
                        id=23, code="same", deleted=False, master=False, is_default=False
                    )
                )
                assert (
                    await connection.scalars(
                        select(table.c.active_key)
                        .where(table.c.code == "same")
                        .order_by(table.c.id)
                    )
                ).all() == [None, None, None, 1]
        finally:
            try:
                if created:
                    async with engine.begin() as connection:
                        await connection.run_sync(table.drop)
            finally:
                await engine.dispose()

    @pytest.mark.parametrize("dialect_name", DdlDialects.names())
    def test_generated_boolean_conditions_compile_for_supported_dialects(self, dialect_name):
        """全部生成列按目标数据库的布尔类型编译。"""
        DdlCli._import_models("module_system")
        DdlCli._import_models("module_infra")
        dialect = DdlDialects.resolve(dialect_name)
        false_literal, true_literal = ("0", "1") if dialect_name == "dm" else ("false", "true")
        computed_columns = [
            column
            for table in Base.metadata.sorted_tables
            if table.name.startswith(("system_", "infra_"))
            for column in table.c
            if column.computed is not None
        ]
        assert len(computed_columns) == 23
        for column in computed_columns:
            expression = str(
                column.computed.sqltext.compile(
                    dialect=dialect, compile_kwargs={"literal_binds": True}
                )
            )
            assert f"deleted = {false_literal}" in expression, column.table.name
            if column.name == "master_active":
                assert f"master = {true_literal}" in expression
            elif column.name == "default_active":
                assert f"is_default = {true_literal}" in expression
            ddl = str(CreateTable(column.table).compile(dialect=dialect))
            assert "GENERATED ALWAYS AS" in ddl
            assert f"deleted = {false_literal}" in ddl

    def test_generated_keys_follow_deleted_and_default_flags(self):
        """有效标记只在未删除且满足默认配置条件时生成。"""
        metadata = MetaData()
        table = Table(
            "generated_flags",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("deleted", Boolean, nullable=False),
            Column("master", Boolean, nullable=False),
            Column("is_default", Boolean, nullable=False),
            Column(
                "active_key", SmallInteger, Computed(PostDO.__table__.c.active_key.computed.sqltext)
            ),
            Column(
                "master_active",
                SmallInteger,
                Computed(FileConfigDO.__table__.c.master_active.computed.sqltext),
            ),
            Column(
                "default_active",
                SmallInteger,
                Computed(DataSourceConfigDO.__table__.c.default_active.computed.sqltext),
            ),
        )
        engine = create_engine("sqlite://")
        try:
            metadata.create_all(engine)
            with engine.begin() as connection:
                for identifier, (deleted, master, is_default) in enumerate(
                    product((False, True), repeat=3), 1
                ):
                    connection.execute(
                        insert(table).values(
                            id=identifier, deleted=deleted, master=master, is_default=is_default
                        )
                    )
                    keys = connection.execute(
                        select(
                            table.c.active_key, table.c.master_active, table.c.default_active
                        ).where(table.c.id == identifier)
                    ).one()
                    assert keys == (
                        None if deleted else 1,
                        1 if not deleted and master else None,
                        1 if not deleted and is_default else None,
                    )
        finally:
            engine.dispose()

    def test_soft_delete_releases_unique_business_key(self):
        """唯一键拒绝重复有效记录，允许删除后重建及保留多条历史记录。"""
        metadata = MetaData()
        table = Table(
            "generated_unique",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("code", String(32), nullable=False),
            Column("deleted", Boolean, nullable=False),
            Column(
                "active_key", SmallInteger, Computed(PostDO.__table__.c.active_key.computed.sqltext)
            ),
            UniqueConstraint("code", "active_key"),
        )
        engine = create_engine("sqlite://")
        try:
            metadata.create_all(engine)
            with engine.begin() as connection:
                connection.execute(
                    insert(table),
                    [
                        {"id": 1, "code": "same", "deleted": False},
                        {"id": 2, "code": "same", "deleted": True},
                        {"id": 3, "code": "same", "deleted": True},
                    ],
                )
                with pytest.raises(IntegrityError):
                    connection.execute(insert(table).values(id=4, code="same", deleted=False))
                connection.execute(update(table).where(table.c.id == 1).values(deleted=True))
                connection.execute(insert(table).values(id=4, code="same", deleted=False))
                assert connection.execute(
                    select(table.c.active_key).order_by(table.c.id)
                ).scalars().all() == [None, None, None, 1]
        finally:
            engine.dispose()
