import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import ArgumentError, ProgrammingError
from starlette.requests import HTTPConnection

from fixtures.config_factory import ConfigFactory
from framework.common.exception import ConfigurationException, ServiceException
from framework.starter_database.exception.database_error_translator import DatabaseErrorTranslator
from framework.starter_database.public import (
    ConnectionFactory,
    DatabaseErrorCodes,
    DatabaseException,
)
from framework.starter_i18n.config.i18n_options import I18nOptions
from framework.starter_i18n.core.accept_language_parser import AcceptLanguageParser
from framework.starter_i18n.core.i18n_catalog import I18nCatalog
from framework.starter_i18n.public import I18nTranslator
from framework.starter_web.public import RequestContext
from module_infra.controller.admin.data_source.vo.data_source_config_save_req_vo import (
    DataSourceConfigSaveReqVO,
)
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.service.data_source.data_source_config_service_impl import (
    DataSourceConfigServiceImpl,
)
from module_infra.util.codegen.db_schema_utils import DbSchemaUtils
from module_infra.util.data_source.data_source_utils import DataSourceUtils

pytestmark = pytest.mark.unit


@pytest.fixture
def engine(monkeypatch):
    """替换真实引擎，不进行数据库连接。"""
    connection = SimpleNamespace(run_sync=AsyncMock(return_value=[]))
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=False)
    value = SimpleNamespace(dispose=AsyncMock(), connect=MagicMock(return_value=context))
    monkeypatch.setattr(ConnectionFactory, "create", MagicMock(return_value=value))
    monkeypatch.setattr(ConnectionFactory, "probe", AsyncMock())
    return value


@pytest.mark.parametrize("utility_type", [DataSourceUtils, DbSchemaUtils])
async def test_utilities_share_temporary_engine_and_preserve_settings(engine, utility_type):
    """两个工具复用原始配置且各只释放一次引擎。"""
    utility = utility_type()
    utility.settings = object()
    config = SimpleNamespace(url="mysql+aiomysql://fixture@localhost/demo")
    if utility_type is DataSourceUtils:
        assert await utility.test_connection(config) is None
        ConnectionFactory.probe.assert_awaited_once_with(engine)
    else:
        assert await utility.get_table_list(config) == []
    source, settings = ConnectionFactory.create.call_args.args
    assert source.url.get_secret_value() == config.url
    assert source.pool is None and source.tls is None
    assert settings is utility.settings
    engine.dispose.assert_awaited_once_with()


@pytest.mark.parametrize("primary", [RuntimeError("query"), asyncio.CancelledError("original")])
async def test_temporary_engine_preserves_primary_when_disposal_also_fails(engine, primary):
    """主错误和原始取消均不能被释放错误替换。"""
    cleanup = RuntimeError("dispose")
    engine.dispose.side_effect = cleanup
    with pytest.raises(type(primary)) as raised:
        async with ConnectionFactory.temporary_engine(object(), object()):
            raise primary
    assert raised.value is primary
    assert raised.value.__cause__.exceptions == (cleanup,)
    engine.dispose.assert_awaited_once_with()


async def test_temporary_engine_keeps_cancellation_during_disposal_and_all_errors(engine):
    """释放期间重复取消仍等待清理完成，并保留主错误及清理失败。"""
    started = asyncio.Event()
    finished = asyncio.Event()
    primary = RuntimeError("query")
    cleanup = RuntimeError("dispose")

    async def dispose():
        """用事件控制清理完成，不访问外部资源。"""
        started.set()
        await finished.wait()
        raise cleanup

    async def execute():
        """让查询异常进入引擎的统一清理路径。"""
        async with ConnectionFactory.temporary_engine(object(), object()):
            raise primary

    engine.dispose.side_effect = dispose
    task = asyncio.create_task(execute())
    await started.wait()
    task.cancel("first")
    await asyncio.sleep(0)
    task.cancel("second")
    await asyncio.sleep(0)
    assert not task.done()
    finished.set()
    with pytest.raises(asyncio.CancelledError) as raised:
        await task
    assert raised.value.__cause__.exceptions == (primary, cleanup)
    engine.dispose.assert_awaited_once_with()


async def test_temporary_engine_reports_disposal_failure_after_success(engine):
    """没有主错误时，释放失败必须显式传播。"""
    cleanup = RuntimeError("dispose")
    engine.dispose.side_effect = cleanup
    with pytest.raises(ExceptionGroup) as raised:
        async with ConnectionFactory.temporary_engine(object(), object()):
            pass
    assert raised.value.exceptions == (cleanup,)


@pytest.mark.parametrize(
    "error", [ValueError("sync dialect"), ArgumentError("bad url"), ModuleNotFoundError("driver")]
)
async def test_temporary_engine_limits_configuration_conversion_to_creation(monkeypatch, error):
    """仅构建阶段已知配置错误归一化，原因链保留供内部诊断。"""
    monkeypatch.setattr(ConnectionFactory, "create", MagicMock(side_effect=error))
    with pytest.raises(ConfigurationException) as raised:
        async with ConnectionFactory.temporary_engine(object(), object()):
            pytest.fail("无效配置不能进入连接体")
    assert raised.value.__cause__ is error


@pytest.mark.parametrize("error", [AttributeError("bug"), ValueError("bug")])
async def test_probe_programming_errors_propagate_unchanged(engine, error):
    """探测体内的程序错误不会被误标为配置或连接失败。"""
    ConnectionFactory.probe.side_effect = error
    utility = DataSourceUtils()
    utility.settings = object()
    with pytest.raises(type(error)) as raised:
        await utility.test_connection(SimpleNamespace(url="mysql+aiomysql://localhost/demo"))
    assert raised.value is error
    engine.dispose.assert_awaited_once_with()


@pytest.fixture
def service():
    """注入实际双语目录和伪造探测器，不初始化应用或数据库。"""
    value = DataSourceConfigServiceImpl()
    value.data_source_utils = SimpleNamespace(test_connection=AsyncMock())
    value.data_source_config_mapper = SimpleNamespace(select_by_id=AsyncMock())
    options = ConfigFactory.build(I18nOptions, "i18n")
    root = (
        Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra/definitions/i18n"
    )
    bundles = {}
    for locale in ("zh-CN", "en-US"):
        messages = json.loads((root / f"{locale}.json").read_text(encoding="utf-8"))["infra"][
            "data_source"
        ]
        bundles[locale] = {
            "infra": {f"infra.data_source.{key}": text for key, text in messages.items()}
        }
    value.translator = I18nTranslator(I18nCatalog(bundles, options), AcceptLanguageParser(options))
    return value


@pytest.mark.parametrize(
    "error",
    [
        ConfigurationException(msg="private-fixture-password"),
        DatabaseException(error_code=DatabaseErrorCodes.CONNECTION_FAILED),
        ConnectionRefusedError("private-fixture-password"),
        TimeoutError("private-fixture-password"),
    ],
)
async def test_connection_failures_keep_cause_without_exposing_details(service, error):
    """只公开安全异常类别，同时保留原始原因。"""
    service.data_source_utils.test_connection.side_effect = error
    with pytest.raises(ServiceException) as raised:
        await service._require_connection(object())
    assert raised.value.error_code is ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED
    assert raised.value.__cause__ is error
    assert "private-fixture-password" not in raised.value.msg


@pytest.mark.parametrize(
    "error",
    [
        AttributeError("bug"),
        ValueError("bug"),
        DatabaseException(error_code=DatabaseErrorCodes.PROGRAMMING_ERROR),
        asyncio.CancelledError("cancelled"),
    ],
)
async def test_non_connection_failures_are_not_business_results(service, error):
    """程序错误、数据库编程错误与取消保持其终止语义。"""
    service.data_source_utils.test_connection.side_effect = error
    with pytest.raises(type(error)) as raised:
        await service._require_connection(object())
    assert raised.value is error


async def test_translated_sql_programming_error_is_not_connection_failure(service):
    """实际 SQLAlchemy 编程错误经过框架分类后仍不能降级成连接失败。"""

    async def probe(config):
        """使用真实异常翻译边界模拟驱动返回的语句错误。"""
        with DatabaseErrorTranslator.boundary(dialect="postgresql", phase="connect"):
            raise ProgrammingError("SELECT invalid", {}, Exception("syntax error"))

    service.data_source_utils.test_connection.side_effect = probe
    with pytest.raises(DatabaseException) as raised:
        await service._require_connection(object())
    assert raised.value.error_code is DatabaseErrorCodes.PROGRAMMING_ERROR


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
@pytest.mark.parametrize("result", ["success", "failure", "missing"])
async def test_connection_result_contract_is_translated(service, locale, result):
    """测试出口保留布尔值与消息元组，并按请求语言翻译三个结果。"""
    service.data_source_config_mapper.select_by_id.return_value = (
        None if result == "missing" else object()
    )
    if result == "failure":
        service.data_source_utils.test_connection.side_effect = ConnectionRefusedError("secret")
    connection = HTTPConnection(
        {"type": "http", "headers": [(b"accept-language", locale.encode())]}
    )
    with RequestContext.bind(connection, "test", "127.0.0.1"):
        success, message = await service.test_data_source_config(1)
    expected = {
        "zh-CN": {
            "success": "连接成功",
            "failure": "数据源连接测试失败：ConnectionRefusedError",
            "missing": "数据源配置不存在",
        },
        "en-US": {
            "success": "Connection successful",
            "failure": "Data source connection test failed: ConnectionRefusedError",
            "missing": "Data source configuration does not exist",
        },
    }
    assert (success, message) == (result == "success", expected[locale][result])
    assert "secret" not in message


@pytest.mark.parametrize("operation", ["create", "update"])
async def test_create_and_update_use_one_connection_requirement(service, operation):
    """两个写入口在数据库操作前统一走相同的连接要求。"""
    service._validate_data_source_config_name_unique = AsyncMock()
    service._validate_data_source_config_exists = AsyncMock(
        return_value=SimpleNamespace(url="mysql+aiomysql://old/demo")
    )
    failure = ServiceException(ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED, "connection")
    service._require_connection = AsyncMock(side_effect=failure)
    request = DataSourceConfigSaveReqVO(
        id="1",
        name="fixture",
        url="mysql+aiomysql://new/demo",
        status=1,
        db_type="mysql",
        source_type=1,
    )
    method = getattr(type(service), f"{operation}_data_source_config").__wrapped__
    with pytest.raises(ServiceException) as raised:
        await method(service, request)
    assert raised.value is failure
    service._require_connection.assert_awaited_once()


@pytest.mark.parametrize("url", ["not-a-url", "mysql://localhost/demo"])
async def test_invalid_url_is_safe_connection_failure(service, url):
    """畸形地址和缺失驱动在配置边界失败，不暴露原始输入。"""
    utility = DataSourceUtils()
    service.data_source_utils = utility
    with pytest.raises(ServiceException) as raised:
        await service._require_connection(SimpleNamespace(url=url))
    assert raised.value.error_code is ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED
    assert url not in raised.value.msg


@pytest.mark.parametrize(
    "url",
    [
        "mysql+missing_fixture_driver://fixture:private-fixture-password@127.0.0.1:1/demo",
        "sqlite+pysqlite:///:memory:",
    ],
)
async def test_unavailable_or_sync_driver_is_configuration_failure_without_connecting(service, url):
    """真实方言加载拒绝未知或同步驱动，且不会尝试连接数据库。"""
    utility = DataSourceUtils()
    utility.settings = object()
    service.data_source_utils = utility
    with pytest.raises(ServiceException) as raised:
        await service._require_connection(SimpleNamespace(url=url))
    assert raised.value.error_code is ErrorCodeConstants.DATA_SOURCE_CONFIG_TEST_FAILED
    assert isinstance(raised.value.__cause__, ConfigurationException)
    assert "private-fixture-password" not in raised.value.msg


async def test_create_requires_url_before_probe(service):
    """创建时缺失地址使用可翻译的独立错误码。"""
    service._validate_data_source_config_name_unique = AsyncMock()
    request = DataSourceConfigSaveReqVO(name="fixture", status=1, db_type="mysql", source_type=1)
    with pytest.raises(ServiceException) as raised:
        await type(service).create_data_source_config.__wrapped__(service, request)
    assert raised.value.error_code is ErrorCodeConstants.DATA_SOURCE_CONFIG_URL_REQUIRED
    service.data_source_utils.test_connection.assert_not_awaited()
