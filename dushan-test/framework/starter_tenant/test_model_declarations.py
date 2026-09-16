import importlib
from uuid import uuid4

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, UniqueConstraint

from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.enums.tenant_model_kind import TenantModelKind
from framework.starter_tenant.exception.tenant_exception import TenantException
from framework.starter_tenant.model.tenant_model import TenantModel
from server.bootstrap.bootstrapper import BootstrapError
from server.starter_server import create_app


def test_model_requires_nonnullable_tenant_and_scoped_unique_key():
    metadata = MetaData()
    table = Table(
        "invalid",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tenant_id", String, nullable=False),
        Column("name", String),
        UniqueConstraint("name"),
    )
    with pytest.raises(TenantException):
        TenantModelRegistry([TenantModel(table, TenantModelKind.TENANT, "tenant_id")])
    with pytest.raises(ValueError):
        TenantModel(table, TenantModelKind.GLOBAL, "tenant_id")


async def test_unmarked_orm_model_fails_startup_even_without_scanner_tag(
    config_dir, module_package
):
    name = "unmarked_tenant_" + uuid4().hex
    source = """from sqlalchemy import MetaData
from framework.starter_database.model.base_do import BaseDO
class Unmarked(BaseDO):
    metadata=MetaData()
    __tablename__="unmarked"
"""
    module_package(name, name=name, scan_roots=(".",), files={"models.py": source})
    importlib.import_module(name + ".models")
    app = create_app(
        base_dir=config_dir(
            {
                "banner": {"enabled": False},
                "modules": {"packages": ["framework", name], "enabled": ["framework", name]},
            }
        ),
        environ={},
    )
    with pytest.raises(BootstrapError) as failure:
        async with app.router.lifespan_context(app):
            pass
    assert isinstance(failure.value.__cause__, TenantException)
    assert failure.value.__cause__.reason == "model"
