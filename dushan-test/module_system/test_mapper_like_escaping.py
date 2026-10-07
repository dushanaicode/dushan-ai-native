import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_system.controller.admin.dict.vo.data.dict_data_page_req_vo import DictDataPageReqVO
from module_system.controller.admin.notification.vo.notice_log.notice_log_page_req_vo import (
    NoticeLogPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_my_page_req_vo import (
    NoticeMessageMyPageReqVO,
)
from module_system.controller.admin.notification.vo.notice_message.notice_message_page_req_vo import (
    NoticeMessagePageReqVO,
)
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.mapper.dict.dict_data_mapper import DictDataMapper
from module_system.dal.mapper.notification.notice_log_mapper import NoticeLogMapper
from module_system.dal.mapper.notification.notice_message_mapper import NoticeMessageMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper

pytestmark = pytest.mark.unit
BACKEND = Path(__file__).resolve().parents[2] / "dushan-admin-backend"
MAPPERS = sorted(
    path
    for module in ("module_system", "module_infra")
    for path in (BACKEND / module / "dal/mapper").rglob("*.py")
    if ".like(" in path.read_text(encoding="utf-8") or ".ilike(" in path.read_text(encoding="utf-8")
)


class TestMapperLikeEscaping:
    @pytest.mark.parametrize("path", MAPPERS, ids=lambda path: path.stem)
    def test_every_mapper_like_declares_escape(self, path):
        """所有业务 LIKE 条件都显式声明转义字符。"""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"like", "ilike"}
            ):
                escapes = [arg.value for arg in node.keywords if arg.arg == "escape"]
                assert len(escapes) == 1, f"{path}:{node.lineno} 未指定 escape"
                assert ast.literal_eval(escapes[0]) == "\\"

    @staticmethod
    async def _statement(mapper, method, **kwargs):
        """保留真实 Mapper 条件构造，只替换数据库执行入口。"""
        mapper.read = AsyncMock(return_value=MagicMock())
        mapper.paginate_query = AsyncMock()
        await getattr(mapper, method)(**kwargs)
        execution = mapper.read if mapper.read.called else mapper.paginate_query
        return execution.call_args.args[0]

    @staticmethod
    def _assert_matches(statement, column, term, *, prefix=False, extra=None):
        """在无默认转义字符的 SQLite 中验证实际查询的匹配结果。"""
        extra = {} if extra is None else extra
        values = [term, term + "suffix", "prefix" + term + "suffix", "aXb", r"a\Xb", "ab", r"a\\b"]
        table = Table(
            column.table.name,
            MetaData(),
            Column(column.key, String),
            *(
                Column(name, Integer if isinstance(value, int) else String)
                for name, value in extra.items()
            ),
        )
        engine = create_engine("sqlite://")
        try:
            table.create(engine)
            with engine.begin() as connection:
                connection.execute(
                    table.insert(), [{column.key: value, **extra} for value in values]
                )
                query = statement.with_only_columns(column).order_by(None)
                actual = connection.execute(query).scalars().all()
            assert actual == values[: 2 if prefix else 3]
        finally:
            engine.dispose()

    @pytest.mark.parametrize("term", ["a%b", "a_b", r"a\b"])
    async def test_dict_page_matches_literal_characters(self, term):
        """字典模糊搜索将百分号、下划线和反斜杠按字面匹配。"""
        statement = await self._statement(
            DictDataMapper(), "select_page", req_vo=DictDataPageReqVO(label=term)
        )
        self._assert_matches(statement, DictDataDO.label, term)

    @pytest.mark.parametrize("term", ["a%b", "a_b", r"a\b"])
    @pytest.mark.parametrize("method", ["select_list_by_nickname", "select_by_keyword"])
    async def test_user_search_matches_literal_characters(self, term, method):
        """用户列表与多字段 OR 搜索保持字面匹配。"""
        argument = "nickname" if method == "select_list_by_nickname" else "keyword"
        statement = await self._statement(AdminUserMapper(), method, **{argument: term})
        self._assert_matches(statement, AdminUserDO.nickname, term, extra={"mobile": "unrelated"})

    @pytest.mark.parametrize("term", ["a%b", "a_b", r"a\b"])
    @pytest.mark.parametrize("mode", ["directory", "prefix", "fuzzy", "scope"])
    async def test_file_search_matches_literal_characters(self, term, mode):
        """目录前缀、文件名前缀、模糊搜索和路径范围都显式转义。"""
        if mode == "directory":
            statement = await self._statement(
                FileMapper(), "select_by_config_and_prefix", config_id=1, storage_path_prefix=term
            )
        else:
            statement = await self._statement(
                FileMapper(),
                "search_files",
                config_id=1,
                keyword="" if mode == "scope" else term,
                search_mode=mode,
                prefix=term if mode == "scope" else "",
                page_no=1,
                page_size=10,
            )
        column = FileDO.storage_path if mode in {"directory", "scope"} else FileDO.name
        self._assert_matches(
            statement, column, term, prefix=mode != "fuzzy", extra={"config_id": 1}
        )

    @pytest.mark.parametrize("term", ["a%b", "a_b", r"a\b"])
    @pytest.mark.parametrize("kind", ["log", "message", "my_message"])
    async def test_notice_title_matches_literal_characters(self, term, kind):
        """通知日志、管理消息和我的消息不接受用户输入的通配符。"""
        if kind == "log":
            statement = await self._statement(
                NoticeLogMapper(), "select_page", req_vo=NoticeLogPageReqVO(notice_title=term)
            )
            column = NoticeLogDO.notice_title
        elif kind == "message":
            statement = await self._statement(
                NoticeMessageMapper(),
                "select_page",
                req_vo=NoticeMessagePageReqVO(notice_title=term),
            )
            column = NoticeMessageDO.notice_title
        else:
            statement = await self._statement(
                NoticeMessageMapper(),
                "select_page_my",
                req_vo=NoticeMessageMyPageReqVO(notice_title=term),
                user_id=1,
                user_type=2,
            )
            column = NoticeMessageDO.notice_title
        self._assert_matches(statement, column, term, extra={"user_id": 1, "user_type": 2})

    def test_dict_data_mapper_has_no_misleading_delete(self):
        """不再暴露实际只计数的删除方法。"""
        assert not hasattr(DictDataMapper, "delete_by_dict_type")
        assert callable(DictDataMapper.select_count_by_dict_type)
