import pytest
from sqlalchemy import MetaData

from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.ddl.ddl_exporter import DdlExporter
from module_infra.dal.dataobject.job.tenant_job_target_do import TenantJobTargetDO
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO


@pytest.mark.parametrize("dialect", DdlDialects.names())
@pytest.mark.parametrize("model", [TenantJobTargetDO, MqOutboxDO])
def test_framework_persistence_tables_compile_for_supported_databases(dialect, model):
    """新持久表在七种正式方言下同时编译列、约束、索引和中文注释。"""
    metadata = MetaData()
    table = model.__table__.to_metadata(metadata)
    script = DdlExporter(metadata, dialect).export(title="框架持久能力建表验证")
    assert f"CREATE TABLE {table.name}" in script
    assert table.comment in script
    for column in table.columns:
        assert column.name in script
        assert column.comment
        assert column.comment in script
    for index in table.indexes:
        assert index.name in script
    assert "UNIQUE" in script
    assert "BIGINT" in script.upper()
