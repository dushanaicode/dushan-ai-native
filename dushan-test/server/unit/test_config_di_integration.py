import importlib

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from fixtures.public_web_app import create_public_app
from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from server.bootstrap.bootstrapper import BootstrapError

pytestmark = pytest.mark.unit


def module_files(*, fail_start=False):
    return {
        "definitions/config/feature_settings.py": (
            "from framework.starter_config.config.config_model import ConfigModel\n"
            "from framework.starter_config.decorator.config_decorator import config_model\n"
            "from pydantic import Field\n"
            "@config_model('feature', env_prefix='FEATURE_')\n"
            "class FeatureSettings(ConfigModel):\n"
            "    label: str\n    count: int = Field(ge=0)\n    enabled: bool\n"
        ),
        "contracts/port.py": "class Port:\n    pass\n",
        "services/repository.py": (
            "from ..contracts.port import Port\n"
            "from ..definitions.config.feature_settings import FeatureSettings\n"
            "from framework.starter_di.decorators.components import repository\n"
            "@repository(interface=Port)\n"
            "class Repository(Port):\n"
            "    def __init__(self, settings: FeatureSettings):\n        self.label = settings.label\n"
        ),
        "services/feature_service.py": (
            "from ..contracts.port import Port\n"
            "from ..definitions.config.feature_settings import FeatureSettings\n"
            "from framework.starter_di.decorators.components import service\n"
            "from framework.starter_di.decorators.inject import Inject\n"
            "@service\n"
            "class FeatureService:\n"
            "    repository: Port = Inject()\n    settings: FeatureSettings = Inject()\n"
            "    events = []\n"
            "    async def post_construct(self):\n        self.events.append('started')\n"
            + ("        raise RuntimeError('integration start failure')\n" if fail_start else "")
            + "    async def pre_destroy(self):\n        self.events.append('closed')\n"
            "    def describe(self):\n        return self.repository.label + '/' + self.settings.label\n"
        ),
    }


def create_feature_app(module_package, config_dir, *, label="base", fail_start=False, environ=None):
    module_package(
        "foundation_feature",
        name="feature",
        files=module_files(fail_start=fail_start),
        scan_roots=("definitions.config", "services"),
    )
    root = config_dir(
        {
            "modules": {
                "packages": ["framework", "foundation_feature"],
                "enabled": ["framework", "feature"],
            },
            "config": {
                "models": {"feature": {"label": label, "count": 1, "enabled": True}},
                "reload_enabled": True,
            },
        }
    )
    app = create_public_app(base_dir=root, environ={} if environ is None else environ)
    add_route(
        app, importlib.import_module("foundation_feature.services.feature_service").FeatureService
    )
    return app


def add_route(app, service_type):
    @app.get("/feature")
    def feature(service=Depends(DiDependency(service_type))):
        return {"code": 0, "message": "ok", "data": {"label": service.describe()}, "error": None}


def test_real_declaration_scan_config_di_http_and_cleanup_chain(module_package, config_dir):
    app = create_feature_app(module_package, config_dir, environ={"FEATURE_LABEL": "environment"})
    assert app.state.bootstrap.definitions is None
    with TestClient(app) as client:
        snapshot = app.state.bootstrap.definitions
        models = snapshot.scan_result.get_components(
            module="feature", component_type=ComponentTypeEnum.CONFIG_MODEL
        )
        services = snapshot.scan_result.get_components(
            module="feature", component_type=ComponentTypeEnum.COMPONENT
        )
        assert len(models) == 1 and len(services) == 2
        service_type = importlib.import_module(
            "foundation_feature.services.feature_service"
        ).FeatureService
        assert snapshot.configuration.get_sources(models[0])["label"] == "环境变量 FEATURE_LABEL"
        assert app.state.application_context is snapshot.application_context
        assert client.get("/feature").json()["data"]["label"] == "environment/environment"
        assert service_type.events == ["started"]
    assert service_type.events == ["started", "closed"]
    assert snapshot.application_context.container.state is ContainerStateEnum.CLOSED
    assert app.state.application_context is None and app.state.bootstrap.definitions is None
    with pytest.raises(BootstrapConfigError, match="已关闭"):
        snapshot.configuration.get_config(models[0])


def test_shared_classes_have_distinct_app_config_and_container_state(module_package, config_dir):
    first = create_feature_app(module_package, config_dir, label="first")
    second = create_feature_app(module_package, config_dir, label="second")
    with TestClient(first) as a:
        cls = importlib.import_module("foundation_feature.services.feature_service").FeatureService
        with TestClient(second) as b:
            assert a.get("/feature").json()["data"]["label"] == "first/first"
            assert b.get("/feature").json()["data"]["label"] == "second/second"
            sa, sb = first.state.bootstrap.definitions, second.state.bootstrap.definitions
            assert (
                sa.configuration is not sb.configuration
                and sa.application_context is not sb.application_context
            )
            with sa.application_context.execution():
                first_service = sa.application_context.container.get(cls)
            with sb.application_context.execution():
                assert first_service is not sb.application_context.container.get(cls)
        assert a.get("/feature").json()["data"]["label"] == "first/first"


def test_config_refresh_changes_explicit_reads_without_mutating_constructor_snapshot(
    module_package, config_dir
):
    app = create_feature_app(module_package, config_dir)
    with TestClient(app) as client:
        cls = importlib.import_module("foundation_feature.services.feature_service").FeatureService
        snapshot = app.state.bootstrap.definitions
        with snapshot.application_context.execution():
            current = snapshot.application_context.container.get(cls)
        snapshot.configuration.replace_memory(
            {"config": {"models": {"feature": {"label": "updated"}}}}
        )
        with snapshot.application_context.execution():
            assert snapshot.application_context.container.get(cls) is current
        assert client.get("/feature").json()["data"]["label"] == "base/updated"


@pytest.mark.parametrize("failure", ["config", "missing_config_definition", "lifecycle"])
def test_failures_do_not_publish_partial_app_definition_or_leave_resources(
    module_package, config_dir, failure
):
    env = (
        {"FEATURE_COUNT": "-1"}
        if failure == "config"
        else {"SCANNER_COMPONENT_TYPES": '["component", "error_code"]'}
        if failure == "missing_config_definition"
        else {}
    )
    app = create_feature_app(
        module_package, config_dir, fail_start=failure == "lifecycle", environ=env
    )
    with pytest.raises(BootstrapError), TestClient(app):
        pass
    service_type = importlib.import_module(
        "foundation_feature.services.feature_service"
    ).FeatureService
    assert service_type.events == (["started", "closed"] if failure == "lifecycle" else [])
    assert app.state.bootstrap.definitions is None and not app.state.bootstrap.ready
    assert app.state.application_context is None
    assert not app.state.bootstrap.logging_starter.initialized


def test_di_disabled_still_loads_config_models_and_does_not_construct_services(
    module_package, config_dir
):
    app = create_feature_app(module_package, config_dir, environ={"DI_ENABLED": "false"})
    with TestClient(app) as client:
        cls = importlib.import_module("foundation_feature.services.feature_service").FeatureService
        snapshot = app.state.bootstrap.definitions
        assert snapshot.application_context is None
        assert (
            len(
                [
                    model
                    for model in snapshot.configuration.model_classes
                    if model.__module__.startswith("foundation_feature.")
                ]
            )
            == 1
        )
        assert cls.events == []
        assert client.get("/feature").json()["code"] == DiErrorCodes.NOT_READY.code


@pytest.mark.parametrize("automatic", [False, True])
def test_explicit_config_and_di_use_the_same_catalog_with_or_without_scan(
    module_package, config_dir, automatic
):
    module_package(
        "foundation_feature",
        name="feature",
        files=module_files(),
        definitions=(
            "definitions.config.feature_settings:FeatureSettings",
            "services.repository:Repository",
            "services.feature_service:FeatureService",
        ),
    )
    root = config_dir(
        {
            "modules": {
                "packages": ["framework", "foundation_feature"],
                "enabled": ["framework", "feature"],
            },
            "config": {"models": {"feature": {"label": "explicit", "count": 1, "enabled": True}}},
            "scanner": {"enabled": automatic},
        }
    )
    app = create_public_app(base_dir=root, environ={})
    cls = importlib.import_module("foundation_feature.services.feature_service").FeatureService
    add_route(app, cls)
    with TestClient(app) as client:
        cls = importlib.import_module("foundation_feature.services.feature_service").FeatureService
        assert client.get("/feature").json()["data"]["label"] == "explicit/explicit"
        definitions = app.state.bootstrap.definitions.scan_result.definitions
        assert len([item for item in definitions if item.module == "feature"]) == 3
