import sys
import types

import pytest
from config_factory import ConfigFactory

from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.dependency_plan import DependencyPlan
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit

HEADER = (
    "from __future__ import annotations\n"
    "from typing import TYPE_CHECKING, Optional\n"
    "from framework.starter_di.decorators.components import repository, service\n"
    "from framework.starter_di.decorators.inject import Inject\n"
    "if TYPE_CHECKING:\n"
    "    from decimal import Decimal as HiddenAmount\n"
)


@pytest.fixture
def configuration(config_dir):
    current = ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [])
    yield current
    current.close()


@pytest.fixture
def load_module(monkeypatch):
    """把使用 `from __future__ import annotations` 的源码装载为真实模块。"""

    def create(name, source):
        module = types.ModuleType(name)
        module.__file__ = f"<{name}>"
        monkeypatch.setitem(sys.modules, name, module)
        exec(compile(HEADER + source, f"<{name}>", "exec"), module.__dict__)
        return module

    return create


def container(components, configuration):
    return DiContainer(
        components,
        configuration=configuration,
        settings=ConfigFactory.build(DiSettings, "di"),
        enabled_modules=frozenset(),
    )


async def test_annotations_outside_injection_points_do_not_block_startup(
    load_module, configuration
):
    module = load_module(
        "di_plan_hidden",
        "@repository\nclass Repo: pass\n"
        "@service\nclass Consumer:\n"
        "    repo: Repo = Inject()\n"
        "    note: HiddenNote\n"
        "    plain: HiddenPlain = None\n"
        "    def __init__(self, repo: Repo, limit: HiddenLimit = 10, *args: HiddenArgs,"
        " **kwargs: HiddenKwargs) -> HiddenReturn:\n"
        "        self.constructor_repo = repo\n",
    )
    plan = DependencyPlan.build(module.Consumer)
    assert plan.fields == (("repo", module.Repo),)
    assert plan.keyword == (("repo", module.Repo),) and plan.positional == ()
    current = container([module.Repo, module.Consumer], configuration)
    await current.startup()
    try:
        consumer = current.get(module.Consumer)
        assert consumer.repo is consumer.constructor_repo is current.get(module.Repo)
    finally:
        await current.shutdown()


@pytest.mark.parametrize(
    "source,target,cause",
    [
        ("    def __init__(self, amount: HiddenAmount): pass\n", "构造参数 amount", NameError),
        ("    cache: HiddenCache = Inject()\n", "字段 cache", NameError),
        ("    def __init__(self, repo): pass\n", "构造参数 repo", TypeError),
        ("    cache = Inject()\n", "字段 cache", TypeError),
        ("    def __init__(self, repo: Optional[Repo]): pass\n", "构造参数 repo", TypeError),
        ("    def __init__(self, repo: 'Broken('): pass\n", "构造参数 repo", SyntaxError),
    ],
)
async def test_unresolvable_injection_points_name_component_and_target(
    load_module, configuration, source, target, cause
):
    module = load_module(
        "di_plan_required",
        "@repository\nclass Repo: pass\n"
        "@service\nclass Consumer:\n" + source + "    def post_construct(self):\n"
        "        raise AssertionError('声明无效的组件不应构造')\n",
    )
    with pytest.raises(DiException) as caught:
        DependencyPlan.build(module.Consumer)
    assert caught.value.error_code == DiErrorCodes.INVALID_DEFINITION
    assert "di_plan_required.Consumer" in str(caught.value) and target in str(caught.value)
    assert isinstance(caught.value.__cause__, cause)
    current = container([module.Repo, module.Consumer], configuration)
    with pytest.raises(DiException) as startup:
        await current.startup()
    assert startup.value.error_code == DiErrorCodes.INVALID_DEFINITION
    assert current.state is ContainerStateEnum.CLOSED


def test_inherited_annotations_resolve_in_the_declaring_module(load_module):
    base = load_module(
        "di_plan_base",
        "@repository\nclass Unit: pass\n"
        "@repository\nclass Repo: pass\n"
        "class Base:\n"
        "    repo: Repo = Inject()\n"
        "    def __init__(self, unit: Unit, /, flag: HiddenFlag = None):\n"
        "        self.unit = unit\n",
    )
    child = load_module(
        "di_plan_child",
        "from di_plan_base import Base\n"
        "@repository\nclass OtherRepo: pass\n"
        "@service\nclass Child(Base): pass\n"
        "@service\nclass Override(Base):\n"
        "    repo: OtherRepo\n",
    )
    assert "Repo" not in vars(child) and "Unit" not in vars(child)
    plan = DependencyPlan.build(child.Child)
    assert plan.fields == (("repo", base.Repo),)
    assert plan.positional == (("unit", base.Unit),) and plan.keyword == ()
    assert DependencyPlan.build(child.Override).fields == (("repo", child.OtherRepo),)


def test_string_forms_positional_only_and_list_dependencies_stay_supported(load_module):
    module = load_module(
        "di_plan_strings",
        "@repository\nclass Repo: pass\n"
        "@service\nclass Consumer:\n"
        "    items: list['Repo'] = Inject()\n"
        "    def __init__(self, first: 'Repo', /, second: Repo, third: 'list[Repo]'): pass\n",
    )
    plan = DependencyPlan.build(module.Consumer)
    assert plan.fields == (("items", list[module.Repo]),)
    assert plan.positional == (("first", module.Repo),)
    assert plan.keyword == (("second", module.Repo), ("third", list[module.Repo]))
    assert plan.dependencies == (module.Repo, module.Repo, list[module.Repo], list[module.Repo])


def test_slots_only_component_cannot_use_field_injection():
    class Repo:
        pass

    class Slotted:
        __slots__ = ()
        repo: Repo = Inject()

    with pytest.raises(DiException, match="__dict__") as caught:
        DependencyPlan.build(Slotted)
    assert caught.value.error_code == DiErrorCodes.INVALID_DEFINITION
