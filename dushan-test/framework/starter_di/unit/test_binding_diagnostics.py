import dataclasses

import pytest

from fixtures.config_factory import ConfigFactory
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.definitions.enums.binding_outcome_enum import BindingOutcomeEnum
from framework.starter_di.definitions.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit


@pytest.fixture
def configuration(config_dir):
    current = ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [])
    yield current
    current.close()


def container(components, configuration, *, enabled_modules=frozenset()):
    return DiContainer(
        components,
        configuration=configuration,
        settings=ConfigFactory.build(DiSettings, "di"),
        enabled_modules=enabled_modules,
    )


def by_component(current):
    return {item.component.rsplit(".", 1)[1]: item for item in current.get_binding_diagnostics()}


async def test_diagnostics_explain_selected_replaced_condition_and_missing_module(configuration):
    calls = {"selected": 0, "inactive": 0}

    class Port:
        pass

    @service(interface=Port)
    class Default(Port):
        pass

    def selected_condition(config):
        calls["selected"] += 1
        return True

    def inactive_condition(config):
        calls["inactive"] += 1
        return False

    @conditional(selected_condition)
    @service(interface=Port)
    class Selected(Port):
        pass

    @conditional(inactive_condition)
    @service(interface=Port)
    class Inactive(Port):
        pass

    @service(depends_on=("billing", "audit"))
    class Optional:
        pass

    @service
    class Plain:
        pass

    current = container([Default, Selected, Inactive, Optional, Plain], configuration)
    assert current.get_binding_diagnostics() == ()
    await current.startup()
    try:
        first = current.get_binding_diagnostics()
        second = current.get_binding_diagnostics()
        assert isinstance(first, tuple) and first == second
        assert calls == {"selected": 1, "inactive": 1}
        items = by_component(current)
        assert {name: item.outcome for name, item in items.items()} == {
            "Default": BindingOutcomeEnum.DEFAULT_REPLACED,
            "Selected": BindingOutcomeEnum.SELECTED,
            "Inactive": BindingOutcomeEnum.CONDITION_FALSE,
            "Optional": BindingOutcomeEnum.MISSING_MODULE,
            "Plain": BindingOutcomeEnum.SELECTED,
        }
        assert "Selected" in items["Default"].reason
        assert "audit, billing" in items["Optional"].reason
        assert all(item.key.endswith("Port") for item in (items["Default"], items["Inactive"]))
        with pytest.raises(dataclasses.FrozenInstanceError):
            items["Default"].reason = "changed"
        assert isinstance(current.get(Port), Selected)
        assert "candidates" not in current.get_statistics()
    finally:
        await current.shutdown()
    assert current.get_binding_diagnostics() == first


async def test_missing_binding_names_known_candidates_and_survives_failed_startup(configuration):
    class Port:
        pass

    @service(interface=Port, depends_on=("billing",))
    class Impl(Port):
        pass

    @service
    class Consumer:
        port: Port = Inject()

        def __init__(self):
            pytest.fail("缺少依赖时不应构造")

    current = container([Impl, Consumer], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.MISSING_BINDING
    message = str(caught.value)
    assert "Consumer" in message and "Impl" in message and "billing" in message
    assert current.state is ContainerStateEnum.CLOSED
    items = by_component(current)
    assert items["Impl"].outcome is BindingOutcomeEnum.MISSING_MODULE
    enabled = container([Impl, Consumer], configuration, enabled_modules=frozenset({"billing"}))
    with pytest.raises(BaseException, match="缺少依赖时不应构造"):
        await enabled.startup()


async def test_missing_binding_without_candidates_and_list_providers_are_explained(configuration):
    class Unknown:
        pass

    class Handler:
        pass

    @service(providers=[Handler], depends_on=("plugins",))
    class Plugin(Handler):
        pass

    @service
    class NeedsUnknown:
        dependency: Unknown = Inject()

    @service
    class NeedsHandlers:
        handlers: list[Handler] = Inject()

    with pytest.raises(DiException) as unknown:
        await container([NeedsUnknown], configuration).startup()
    assert unknown.value.error_code == DiErrorCodes.MISSING_BINDING
    assert "Unknown" in str(unknown.value) and "没有任何候选" in str(unknown.value)
    with pytest.raises(DiException) as handlers:
        await container([Plugin, NeedsHandlers], configuration).startup()
    assert handlers.value.error_code == DiErrorCodes.MISSING_BINDING
    assert "list[" in str(handlers.value) and "Plugin" in str(handlers.value)
    assert "plugins" in str(handlers.value)


async def test_conflicts_are_recorded_for_every_candidate_and_still_fail_startup(configuration):
    class Port:
        pass

    @service(interface=Port)
    class First(Port):
        pass

    @service(interface=Port)
    class Second(Port):
        pass

    @conditional(lambda config: pytest.fail("默认候选冲突后不应再求值条件"))
    @service(interface=Port)
    class Conditional(Port):
        pass

    current = container([First, Second, Conditional], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.DUPLICATE_BINDING
    items = by_component(current)
    assert items["First"].outcome is items["Second"].outcome is BindingOutcomeEnum.CONFLICT
    assert "Second" in items["First"].reason and "First" in items["Second"].reason
    assert "Conditional" not in items


async def test_runtime_lookup_of_unbound_key_explains_skipped_candidates(configuration):
    class Port:
        pass

    @conditional(lambda config: False)
    @service(interface=Port)
    class Inactive(Port):
        pass

    current = container([Inactive], configuration)
    await current.startup()
    try:
        with pytest.raises(DiException) as caught:
            current.get(Port)
        assert caught.value.error_code == DiErrorCodes.MISSING_BINDING
        assert "Inactive" in str(caught.value) and "条件不满足" in str(caught.value)
    finally:
        await current.shutdown()
