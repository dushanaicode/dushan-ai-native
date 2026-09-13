from uuid import uuid4

import pytest
from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, String, Table, insert, select
from sqlalchemy.ext.asyncio import create_async_engine

from fixtures.database_fixtures import TARGETS
from framework.starter_database.exception.database_error_codes import DatabaseErrorCodes
from framework.starter_database.exception.database_exception import DatabaseException
from framework.starter_database.session.session_provider import SessionProvider


@pytest.mark.parametrize(
    "database_settings",
    [target for target in TARGETS if target["name"] != "sqlite"],
    indirect=True,
    ids=lambda target: target["name"],
)
async def test_unique_foreign_key_and_index_keep_data_integrity(database_settings):
    suffix = uuid4().hex[:12]
    metadata = MetaData()
    parent = Table(
        "native_parent_" + suffix,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(32), unique=True, nullable=False),
    )
    child = Table(
        "native_child_" + suffix,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey(parent.c.id), nullable=False),
    )
    Index("native_idx_" + suffix, child.c.parent_id)
    schema = create_async_engine(database_settings.sources[0].url.get_secret_value())
    database = SessionProvider(database_settings)
    try:
        async with schema.begin() as connection:
            await connection.run_sync(metadata.create_all)
        async with database.lifespan():
            async with database.transaction() as session:
                await session.execute(insert(parent).values(id=1, name="unique"))
                await session.execute(insert(child).values(id=1, parent_id=1))
            with pytest.raises(DatabaseException) as unique_error:
                async with database.transaction() as session:
                    await session.execute(insert(parent).values(id=2, name="unique"))
            assert unique_error.value.error_code == DatabaseErrorCodes.UNIQUE_VIOLATION
            with pytest.raises(DatabaseException) as foreign_key_error:
                async with database.transaction() as session:
                    await session.execute(insert(child).values(id=2, parent_id=999))
            assert foreign_key_error.value.error_code == DatabaseErrorCodes.FOREIGN_KEY_VIOLATION
            async with database.read_session() as session:
                assert (await session.execute(select(parent.c.id))).scalars().all() == [1]
                assert (await session.execute(select(child.c.id))).scalars().all() == [1]
    finally:
        try:
            async with schema.begin() as connection:
                await connection.run_sync(metadata.drop_all)
        finally:
            await schema.dispose()
