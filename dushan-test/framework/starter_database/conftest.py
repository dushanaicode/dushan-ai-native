from uuid import uuid4

import pytest
from sqlalchemy import JSON, LargeBinary, MetaData, Numeric, String
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import mapped_column

from fixtures.config_factory import ConfigFactory
from fixtures.database_fixtures import TARGETS
from framework.common.page.config.page_settings import PageSettings
from framework.common.page.core.data_paginator import DataPaginator
from framework.starter_database.config.database_settings import DatabaseSettings
from framework.starter_database.model.base_do import BaseDO
from framework.starter_database.repository.base_mapper import BaseMapper
from framework.starter_database.session.session_provider import SessionProvider


@pytest.fixture(params=TARGETS, ids=lambda target: target["name"])
def database_settings(request, tmp_path):
    values = ConfigFactory.values()["config"]["models"]["database"]
    url = request.param["url"] or f"sqlite+aiosqlite:///{(tmp_path / 'database.sqlite').as_posix()}"
    values.update(
        enabled=True, health_check_enabled=False, slow_query_enabled=False, dynamic_enabled=True
    )
    values["pool"].update(size=8, max_overflow=0, timeout_seconds=2)
    values["connect_timeout_seconds"] = 2
    values["sources"] = [
        dict(name="primary", url=url, role="primary", weight=100, pool=None, tls=None)
    ]
    return DatabaseSettings.model_validate(values)


@pytest.fixture
async def database_case(database_settings):
    identifier = uuid4().hex[:16]
    Item = type(
        "DatabaseItem_" + identifier,
        (BaseDO,),
        {
            "__tablename__": "native_db_test_" + identifier,
            "metadata": MetaData(),
            "value": mapped_column(String(64), nullable=True),
            "payload": mapped_column(JSON, nullable=True),
            "amount": mapped_column(Numeric(18, 4), nullable=True),
            "blob": mapped_column(LargeBinary, nullable=True),
        },
    )

    database = SessionProvider(database_settings)
    schema = create_async_engine(database_settings.sources[0].url.get_secret_value())
    mapper = BaseMapper(Item)
    mapper.session_provider = database
    mapper.paginator = DataPaginator(ConfigFactory.build(PageSettings, "page"))
    created = False
    try:
        async with schema.begin() as connection:
            await connection.run_sync(Item.__table__.create)
        created = True
        async with database.lifespan():
            yield database, Item, mapper
    finally:
        try:
            if created:
                async with schema.begin() as connection:
                    await connection.run_sync(Item.__table__.drop)
        finally:
            await schema.dispose()
