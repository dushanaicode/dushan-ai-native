import pytest
from sqlalchemy.schema import CreateTable

from framework.starter_database.ddl.ddl_dialects import DdlDialects
from module_infra.dal.dataobject.mq.mq_outbox_do import MqOutboxDO


class TestMultidbModelTypes:
    @pytest.mark.parametrize("dialect_name", DdlDialects.names())
    def test_outbox_message_uses_unbounded_native_text(self, dialect_name):
        """可靠消息保留 MySQL 大文本容量，其他方言不生成非法 TEXT 长度修饰。"""
        dialect = DdlDialects.resolve(dialect_name)
        expected = "LONGTEXT" if dialect_name in {"mysql", "tidb", "oceanbase"} else "TEXT"
        column = MqOutboxDO.__table__.c.message
        assert column.type.compile(dialect=dialect) == expected
        ddl = str(CreateTable(MqOutboxDO.__table__).compile(dialect=dialect))
        assert f"message {expected} NOT NULL" in ddl
        assert "TEXT(" not in ddl
