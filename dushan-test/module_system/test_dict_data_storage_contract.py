from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select

from module_system.controller.admin.dict.vo.data.dict_data_simple_resp_vo import (
    DictDataSimpleRespVO,
)
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO


@pytest.mark.parametrize(
    "values, expected",
    [
        ({}, None),
        ({"tag_style": None}, None),
        (
            {"tag_style": {"color": "#cf1322", "textColor": "", "variant": "solid"}},
            {"color": "#cf1322", "textColor": "", "variant": "solid"},
        ),
    ],
)
def test_dictionary_style_round_trip_matches_response_contract(values, expected):
    """未设置样式与对象样式持久化后都能直接返回给字典消费者。"""
    engine = create_engine("sqlite://")
    try:
        DictDataDO.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(
                DictDataDO.__table__.insert().values(
                    label="测试标签",
                    value="test",
                    dict_type="test_dictionary",
                    create_time=datetime(2026, 10, 4),
                    update_time=datetime(2026, 10, 4),
                    **values,
                )
            )
            stored = connection.execute(select(DictDataDO.__table__)).mappings().one()
            assert stored["tag_style"] == expected
            response = DictDataSimpleRespVO.model_validate(
                DictDataDO(**stored), from_attributes=True
            )
            assert response.model_dump(by_alias=True)["tagStyle"] == expected
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "relative_path",
    [
        "dushan-admin-backend/sql/mysql/system/02_system_dict_data.sql",
        "dushan-admin-frontend/apps/web-ele/src/constants/dict-types.ts",
    ],
)
def test_retired_menu_dictionary_is_not_published(relative_path):
    """种子和前端字典清单不再发布已由菜单 kind 替代的数字类型。"""
    root = Path(__file__).resolve().parents[2]
    content = (root / relative_path).read_text(encoding="utf-8")
    assert "system_menu_type" not in content
    assert "SYSTEM_MENU_TYPE" not in content
