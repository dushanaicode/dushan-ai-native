import pytest
from sqlalchemy import UniqueConstraint

from framework.starter_database.ddl.ddl_exporter import DdlExporter
from module_system.dal.dataobject.announcement.announcement_do import AnnouncementDO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO
from module_system.definitions.enums.announcement.announcement_status_enum import (
    AnnouncementStatusEnum,
)


@pytest.mark.parametrize(
    "model, expected",
    [
        (
            DictTypeDO,
            {
                "uq_system_dict_type_active_0": ("name", "active_key"),
                "uq_system_dict_type_active_1": ("type", "active_key"),
            },
        ),
        (
            DictDataDO,
            {"uq_system_dict_data_active_0": ("dict_type", "value", "active_key")},
        ),
    ],
)
def test_dictionary_business_keys_are_unique_for_live_records(model, expected):
    """三条已有唯一性规则由可空生成列约束，软删记录不占用业务键。"""
    table = model.__table__
    constraints = {
        constraint.name: tuple(column.name for column in constraint)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert constraints == expected
    assert table.c.active_key.nullable
    assert str(table.c.active_key.computed.sqltext) == (
        "CASE WHEN (deleted = false) THEN :param_1 ELSE NULL END"
    )
    assert table.c.active_key.computed.sqltext.compile().params == {"param_1": 1}


@pytest.mark.parametrize(
    "dialect", ["mysql", "tidb", "oceanbase", "postgresql", "opengauss", "kingbase", "dm"]
)
@pytest.mark.parametrize("model", [DictTypeDO, DictDataDO])
def test_dictionary_constraints_compile_for_each_database(model, dialect):
    """七库离线导出保留字典唯一性，并沿用达梦的软删唯一索引实现。"""
    table = model.__table__
    ddl = DdlExporter(table.metadata, dialect)._table(table)
    assert "CASE WHEN (deleted = " in ddl
    assert "THEN 1 ELSE NULL END" in ddl
    for constraint in table.constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue
        if dialect == "dm":
            assert f"CREATE UNIQUE INDEX {constraint.name} ON {table.name}" in ddl
            assert f"CONSTRAINT {constraint.name} UNIQUE" not in ddl
            assert "CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END" in ddl
        else:
            assert f"CONSTRAINT {constraint.name} UNIQUE" in ddl


def test_announcement_orm_default_is_draft():
    """公告省略状态时仍采用草稿编码，枚举替换不增加数据库默认值。"""
    status = AnnouncementDO.__table__.c.status
    assert status.default.arg == AnnouncementStatusEnum.DRAFT.code == 0
    assert status.server_default is None
