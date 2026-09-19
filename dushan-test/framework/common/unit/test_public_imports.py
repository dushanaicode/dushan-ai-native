import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[4] / "dushan-admin-backend"
STARTER_PACKAGES = (
    "starter_auth",
    "starter_cache",
    "starter_captcha",
    "starter_config",
    "starter_data_permission",
    "starter_database",
    "starter_di",
    "starter_excel",
    "starter_i18n",
    "starter_ip",
    "starter_job",
    "starter_logging",
    "starter_module",
    "starter_monitor",
    "starter_mq",
    "starter_protection",
    "starter_scanner",
    "starter_security",
    "starter_tenant",
    "starter_web",
    "starter_websocket",
)
PUBLIC_MODULES = (
    "framework.common.schemas",
    "framework.common.schemas.request",
    "framework.common.contracts",
    "framework.common.enums",
    "framework.common.dates",
    "framework.common.validator",
    "framework.common.utils",
    "framework.common.page",
    "framework.common.exception",
    "framework.common.security",
    "framework.starter_auth.public",
    "framework.starter_cache.public",
    "framework.starter_captcha.public",
    "framework.starter_config.public",
    "framework.starter_data_permission.public",
    "framework.starter_database.public",
    "framework.starter_di.public",
    "framework.starter_excel.public",
    "framework.starter_i18n.public",
    "framework.starter_ip.public",
    "framework.starter_job.public",
    "framework.starter_logging.public",
    "framework.starter_monitor.public",
    "framework.starter_mq.public",
    "framework.starter_protection.public",
    "framework.starter_scanner.public",
    "framework.starter_security.public",
    "framework.starter_tenant.public",
    "framework.starter_web.public",
    "framework.starter_websocket.public",
)
IMPLEMENTATIONS = tuple(
    ".".join(path.relative_to(BACKEND).with_suffix("").parts).removesuffix(".__init__")
    for package in ("framework/common",)
    + tuple(f"framework/{starter}" for starter in STARTER_PACKAGES)
    for path in sorted((BACKEND / package).rglob("*.py"))
    if "Temp" not in path.parts
)
COLD_IMPORT = """
import importlib
import sys

def reject_connections(event, args):
    if event == "socket.connect":
        raise AssertionError("Import must not open a connection")

sys.addaudithook(reject_connections)
sys.path.insert(0, sys.argv[1])
for name in sys.argv[2:]:
    importlib.import_module(name)
"""

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", IMPLEMENTATIONS)
def test_each_module_imports_first_in_a_fresh_process(name):
    """逐个从空模块缓存导入，暴露父包重导出造成的半初始化回环。"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", COLD_IMPORT, str(BACKEND), name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("name", PUBLIC_MODULES)
def test_public_exports_preserve_original_objects(name):
    """快捷入口只提供原对象，保持 DI 类型身份及定义模块归属。"""
    public = importlib.import_module(name)
    tree = ast.parse(Path(public.__file__).read_text(encoding="utf-8"))
    exports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            source = importlib.import_module(node.module)
            exports.update(
                (alias.asname or alias.name, getattr(source, alias.name)) for alias in node.names
            )
    assert set(public.__all__) == exports.keys()
    for alias, original in exports.items():
        assert getattr(public, alias) is original


def test_cache_public_keeps_original_scanner_and_dependency_contracts(module_package):
    """公共类型能用于真实模块注解，但组件登记仍要求原始定义模块。"""
    from fixtures.config_factory import ConfigFactory
    from framework.starter_cache import public
    from framework.starter_cache.core.cache_handler import CacheHandler
    from framework.starter_di.core.dependency_plan import DependencyPlan
    from framework.starter_scanner.config.scanner_config import ScannerConfig
    from framework.starter_scanner.core.component_collector import ComponentCollector
    from framework.starter_scanner.definitions.constants.scanner_error_codes import (
        ScannerErrorCodes,
    )
    from framework.starter_scanner.exception.scanner_exception import ScannerException

    collector = ComponentCollector(ConfigFactory.build(ScannerConfig, "scanner"))
    source = Path(public.__file__)
    assert collector.collect(public, "framework", source) == ()
    with pytest.raises(ScannerException) as failed:
        collector.definition(public.CacheHandler, public, "framework", source)
    assert failed.value.error_code is ScannerErrorCodes.SCANNER_MISSING_METADATA

    module_package(
        "public_cache_consumer",
        files={
            "consumer.py": (
                "from framework.starter_cache.public import CacheHandler\n"
                "from framework.starter_di.decorators.inject import Inject\n"
                "class Consumer:\n"
                "    cache: 'CacheHandler' = Inject()\n"
                "    def __init__(self, cache: 'CacheHandler'):\n"
                "        self.constructor_cache = cache\n"
            )
        },
    )
    consumer = importlib.import_module("public_cache_consumer.consumer").Consumer
    plan = DependencyPlan.build(consumer)
    assert plan.fields == (("cache", CacheHandler),)
    assert plan.keyword == (("cache", CacheHandler),)


@pytest.mark.parametrize("name", PUBLIC_MODULES[10:])
def test_starter_public_modules_collect_no_component_definitions(name):
    """public.py 的显式重导出不产生新的组件定义，也不被当作原始定义。"""
    from fixtures.config_factory import ConfigFactory
    from framework.starter_scanner.config.scanner_config import ScannerConfig
    from framework.starter_scanner.core.component_collector import ComponentCollector
    from framework.starter_scanner.definitions.constants.scanner_error_codes import (
        ScannerErrorCodes,
    )
    from framework.starter_scanner.exception.scanner_exception import ScannerException

    public = importlib.import_module(name)
    collector = ComponentCollector(ConfigFactory.build(ScannerConfig, "scanner"))
    source = Path(public.__file__)
    assert collector.collect(public, "framework", source) == ()
    for exported in public.__all__:
        value = getattr(public, exported)
        if isinstance(value, type):
            with pytest.raises(ScannerException) as failed:
                collector.definition(value, public, "framework", source)
            assert failed.value.error_code is ScannerErrorCodes.SCANNER_MISSING_METADATA


def test_starter_public_types_resolve_to_original_di_types(module_package):
    """字符串注解与 Inject() 字段经公共入口仍解析到原始定义类型。"""
    from framework.starter_database.public import SessionProvider as PublicSessionProvider
    from framework.starter_database.session.session_provider import SessionProvider
    from framework.starter_di.core.dependency_plan import DependencyPlan
    from framework.starter_di.public import Inject as PublicInject
    from framework.starter_mq.core.mq_service import MQService
    from framework.starter_mq.public import MQService as PublicMQService
    from framework.starter_security.core.security_service import SecurityService
    from framework.starter_security.public import SecurityService as PublicSecurityService

    module_package(
        "public_starter_consumer",
        files={
            "consumer.py": (
                "from framework.starter_database.public import SessionProvider\n"
                "from framework.starter_di.public import Inject\n"
                "from framework.starter_mq.public import MQService\n"
                "from framework.starter_security.public import SecurityService\n"
                "class Consumer:\n"
                "    sessions: 'SessionProvider' = Inject()\n"
                "    mq: 'MQService' = Inject()\n"
                "    def __init__(self, security: 'SecurityService'):\n"
                "        self.security = security\n"
            )
        },
    )
    consumer = importlib.import_module("public_starter_consumer.consumer").Consumer
    plan = DependencyPlan.build(consumer)
    assert PublicSessionProvider is SessionProvider
    assert PublicMQService is MQService
    assert PublicSecurityService is SecurityService
    assert PublicInject is not None
    assert plan.fields == (
        ("mq", MQService),
        ("sessions", SessionProvider),
    )
    assert plan.keyword == (("security", SecurityService),)
