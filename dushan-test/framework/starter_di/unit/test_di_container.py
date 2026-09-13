import asyncio
import threading

import pytest

from fixtures.config_factory import ConfigFactory
from framework.common.enums.base_enum import BaseEnum
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.decorators.components import component, repository, service
from framework.starter_di.decorators.conditional import conditional
from framework.starter_di.decorators.inject import Inject
from framework.starter_di.decorators.lifecycle import post_construct_hook, pre_destroy_hook
from framework.starter_di.enums.component_role_enum import ComponentRoleEnum
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_di.enums.container_state_enum import ContainerStateEnum
from framework.starter_di.exception.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit


@pytest.fixture
def configuration(config_dir):
    current = ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [])
    yield current
    current.close()


def container(
    components, configuration, *, instances=None, enabled_modules=frozenset(), **settings
):
    return DiContainer(
        components,
        configuration=configuration,
        settings=ConfigFactory.build(DiSettings, "di", **settings),
        enabled_modules=enabled_modules,
        instances=instances,
    )


async def test_constructor_and_field_injection_preserve_scopes_and_app_isolation(configuration):
    @repository
    class Repository:
        pass

    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Transient:
        pass

    @service
    class Consumer:
        repository: Repository = Inject()
        transient: Transient = Inject()

        def __init__(self, constructor_repository: Repository):
            self.constructor_repository = constructor_repository

    first = container([Repository, Transient, Consumer], configuration)
    second = container([Repository, Transient, Consumer], configuration)
    with pytest.raises(DiException):
        first.get(Consumer)
    await first.startup()
    await second.startup()
    a, b = first.get(Consumer), second.get(Consumer)
    assert a is first.get(Consumer) and a is not b
    assert a.repository is a.constructor_repository is first.get(Repository)
    assert a.repository is not b.repository
    assert a.transient is not a.transient
    assert a in first.get_by_role(ComponentRoleEnum.SERVICE)
    with pytest.raises(DiException, match="不能覆盖"):
        a.repository = Repository()
    await first.shutdown()
    assert second.get(Consumer) is b
    with pytest.raises(DiException):
        first.get(Consumer)
    await second.shutdown()


async def test_interface_and_provider_lists_reuse_the_original_singleton(configuration):
    class Handler:
        pass

    @service(interface=Handler, providers=[Handler])
    class First(Handler):
        pass

    @service(providers=[Handler])
    class Second(Handler):
        pass

    @service
    class Consumer:
        handlers: list[Handler] = Inject()

    current = container([First, Second, Consumer], configuration)
    await current.startup()
    assert current.get(list[Handler]) == [current.get(Handler), current.get(Second)]
    assert current.get(Consumer).handlers == current.get(list[Handler])
    with pytest.raises(DiException, match="未显式绑定"):
        current.get(First)
    await current.shutdown()


async def test_active_conditions_override_default_and_disabled_dependencies_skip_creation(
    configuration,
):
    class Port:
        pass

    @service(interface=Port)
    class Default(Port):
        pass

    @conditional(lambda config: config.revision == configuration.revision)
    @service(interface=Port)
    class Selected(Port):
        pass

    @conditional(lambda config: False)
    @service(interface=Port)
    class Inactive(Port):
        def __init__(self):
            pytest.fail("不应构造未选中的条件候选")

    @service(depends_on=("optional_module",))
    class Optional:
        def __init__(self):
            pytest.fail("不应构造未启用依赖的组件")

    current = container([Default, Selected, Inactive, Optional], configuration)
    await current.startup()
    assert isinstance(current.get(Port), Selected)
    await current.shutdown()


@pytest.mark.parametrize("conditional_candidates", [False, True])
async def test_conflicts_fail_before_any_constructor(configuration, conditional_candidates):
    events = []

    class Port:
        pass

    @service(interface=Port)
    class First:
        def __init__(self):
            events.append("first")

    @service(interface=Port)
    class Second:
        def __init__(self):
            events.append("second")

    if conditional_candidates:
        First = conditional(lambda config: True)(First)
        Second = conditional(lambda config: True)(Second)
    current = container([First, Second], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.DUPLICATE_BINDING
    assert events == [] and current.state is ContainerStateEnum.CLOSED


async def test_missing_binding_and_cycles_are_detected_before_construction(configuration):
    class Missing:
        pass

    @service
    class First:
        dependency = Inject()

    First.__annotations__ = {"dependency": Missing}
    missing = container([First], configuration)
    with pytest.raises(DiException) as caught:
        await missing.startup()
    assert caught.value.error_code == DiErrorCodes.MISSING_BINDING

    @service
    class Second:
        dependency = Inject()

    First.__annotations__ = {"dependency": Second}
    Second.__annotations__ = {"dependency": First}
    cyclic = container([First, Second], configuration)
    with pytest.raises(DiException) as caught:
        await cyclic.startup()
    assert caught.value.error_code == DiErrorCodes.CIRCULAR_DEPENDENCY


async def test_cycle_through_provider_list_is_detected(configuration):
    class Handler:
        pass

    @service
    class Consumer:
        handlers = Inject()

    @service(providers=[Handler])
    class Provider(Handler):
        consumer: Consumer = Inject()

    Consumer.__annotations__ = {"handlers": list[Handler]}
    current = container([Consumer, Provider], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.CIRCULAR_DEPENDENCY


async def test_lifecycle_order_async_hooks_and_dependency_access_during_cleanup(configuration):
    events = []

    @service
    class Resource:
        async def post_construct(self):
            events.append("resource start")

        async def pre_destroy(self):
            events.append("resource stop")

    @service
    class Consumer:
        resource: Resource = Inject()

        @post_construct_hook
        async def initialize(self):
            assert isinstance(self.resource, Resource)
            events.append("consumer start")

        @pre_destroy_hook
        async def cleanup(self):
            assert isinstance(self.resource, Resource)
            events.append("consumer stop")

    current = container([Consumer, Resource], configuration)
    await current.startup()
    await current.shutdown()
    await current.shutdown()
    assert events == ["resource start", "consumer start", "consumer stop", "resource stop"]


async def test_failed_initialization_cleans_partial_instance_and_all_dependencies(configuration):
    events = []
    original = RuntimeError("original failure")

    @service
    class Resource:
        def pre_destroy(self):
            events.append("resource closed")

    @service
    class Broken:
        resource: Resource = Inject()

        async def post_construct(self):
            events.append("allocated")
            raise original

        async def pre_destroy(self):
            events.append("partial closed")

    current = container([Resource, Broken], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.__cause__ is original
    assert events == ["allocated", "partial closed", "resource closed"]
    assert current.state is ContainerStateEnum.CLOSED


async def test_cleanup_failures_do_not_prevent_remaining_cleanup(configuration):
    events = []

    @service
    class A:
        def pre_destroy(self):
            events.append("a")

    @service
    class B:
        a: A = Inject()

        def pre_destroy(self):
            events.append("b")
            raise ValueError("cleanup failure")

    current = container([A, B], configuration)
    await current.startup()
    with pytest.raises(BaseExceptionGroup):
        await current.shutdown()
    assert events == ["b", "a"] and current.state is ContainerStateEnum.CLOSED


async def test_cancelled_shutdown_wait_returns_promptly_and_destroy_completes_once(configuration):
    entered, release, finished = asyncio.Event(), asyncio.Event(), []

    @service
    class Resource:
        async def pre_destroy(self):
            entered.set()
            await release.wait()
            finished.append(True)

    current = container([Resource], configuration)
    await current.startup()
    closing = asyncio.create_task(current.shutdown())
    await entered.wait()
    closing.cancel("调用方放弃等待")
    with pytest.raises(asyncio.CancelledError):
        await closing
    # 取消的只是等待：销毁钩子仍在运行，容器保持 STOPPING。
    assert not finished and current.state is ContainerStateEnum.STOPPING
    release.set()
    await current.shutdown()
    assert finished == [True] and current.state is ContainerStateEnum.CLOSED


async def test_startup_cancellation_rolls_back_and_hook_timeout_preserves_cause(configuration):
    entered, released = asyncio.Event(), asyncio.Event()

    @service
    class Resource:
        async def post_construct(self):
            entered.set()
            await asyncio.sleep(10)

        async def pre_destroy(self):
            released.set()

    current = container([Resource], configuration)
    starting = asyncio.create_task(current.startup())
    await entered.wait()
    starting.cancel("startup cancelled")
    with pytest.raises(asyncio.CancelledError, match="startup cancelled"):
        await starting
    assert released.is_set() and current.state is ContainerStateEnum.CLOSED
    timed = container([Resource], configuration, hook_timeout_seconds=0.01)
    with pytest.raises(DiException) as caught:
        await timed.startup()
    assert isinstance(caught.value.__cause__, TimeoutError)
    assert timed.state is ContainerStateEnum.CLOSED


async def test_transient_resource_hooks_are_rejected_before_construction(configuration):
    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Invalid:
        def __init__(self):
            pytest.fail("声明无有效销毁边界，不应构造")

        def pre_destroy(self):
            pass

    current = container([Invalid], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.INVALID_LIFECYCLE


async def test_wrong_interface_and_external_instance_fail_at_registration(configuration):
    class Port:
        pass

    @service(interface=Port)
    class Wrong:
        def __init__(self):
            pytest.fail("错误绑定不能进入构造")

    current = container([Wrong], configuration)
    with pytest.raises(DiException) as invalid:
        await current.startup()
    assert invalid.value.error_code == DiErrorCodes.INVALID_DEFINITION
    with pytest.raises(DiException) as instance:
        container([], configuration, instances={Port: object()})
    assert instance.value.error_code == DiErrorCodes.INVALID_DEFINITION


async def test_wrapped_generator_is_not_a_successful_transient_initialization(configuration):
    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Resource:
        def post_construct(self):
            return (value for value in ())

    current = container([Resource], configuration)
    await current.startup()
    try:
        with pytest.raises(DiException) as caught:
            current.get(Resource)
        assert caught.value.error_code == DiErrorCodes.INVALID_LIFECYCLE
    finally:
        await current.shutdown()


async def test_lifecycle_reentrant_shutdown_fails_instead_of_deadlocking(configuration):
    @service
    class Invalid:
        container: DiContainer = Inject()

        async def pre_destroy(self):
            await self.container.shutdown()

    current = container([Invalid], configuration)
    await current.startup()
    with pytest.raises(BaseExceptionGroup):
        await asyncio.wait_for(current.shutdown(), timeout=1)
    assert current.state is ContainerStateEnum.CLOSED


async def test_shutdown_waits_for_an_already_started_thread_resolution(configuration):
    entered, release = threading.Event(), threading.Event()

    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Slow:
        def __init__(self):
            entered.set()
            assert release.wait(timeout=2)

    current = container([Slow], configuration)
    await current.startup()
    get_task = asyncio.create_task(asyncio.to_thread(current.get, Slow))
    assert await asyncio.to_thread(entered.wait, 1)
    closing = asyncio.create_task(current.shutdown())
    await asyncio.sleep(0.02)
    assert not closing.done()
    with pytest.raises(DiException):
        current.get(Slow)
    release.set()
    await get_task
    await closing
    assert current.state is ContainerStateEnum.CLOSED


async def test_new_plugin_role_uses_shared_discovery_without_modifying_core_enum(configuration):
    class PluginRole(BaseEnum):
        HANDLER = ("plugin_handler", "插件处理器")

    handler = component(PluginRole.HANDLER)

    @handler
    class Handler:
        pass

    current = container([Handler], configuration)
    await current.startup()
    assert current.get_by_role(PluginRole.HANDLER) == (current.get(Handler),)
    await current.shutdown()


def test_inject_descriptor_cannot_be_reused_for_multiple_fields():
    descriptor = Inject()
    with pytest.raises(TypeError, match="不能绑定多个字段"):

        class Invalid:
            first = descriptor
            second = descriptor


def test_component_dependencies_reject_a_string_instead_of_scanning_its_characters():
    with pytest.raises(TypeError, match="不能是字符串"):
        service(depends_on="abc")


async def test_background_task_does_not_keep_expired_lifecycle_permission(configuration):
    release = asyncio.Event()

    @service
    class Resource:
        current: DiContainer = Inject()

        async def post_construct(self):
            async def later():
                await release.wait()
                await self.current.shutdown()

            self.task = asyncio.create_task(later())

    current = container([Resource], configuration)
    await current.startup()
    task = current.get(Resource).task
    release.set()
    try:
        await task
        assert current.state is ContainerStateEnum.CLOSED
    finally:
        await current.shutdown()


async def test_child_task_does_not_reuse_finished_resolution_path(configuration):
    release, tasks = asyncio.Event(), []

    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Resource:
        def __init__(self, current: DiContainer):
            if not tasks:

                async def later():
                    await release.wait()
                    return current.get(Resource)

                tasks.append(asyncio.create_task(later()))

    current = container([Resource], configuration)
    await current.startup()
    first = current.get(Resource)
    release.set()
    try:
        assert await tasks[0] is not first
    finally:
        await current.shutdown()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_generator_lifecycle_is_rejected_before_construction(configuration, asynchronous):
    def sync_hook(self):
        yield

    async def async_hook(self):
        yield

    @service
    class Resource:
        def __init__(self):
            pytest.fail("无效生命周期不能进入构造阶段")

    Resource.post_construct = async_hook if asynchronous else sync_hook
    current = container([Resource], configuration)
    with pytest.raises(DiException) as caught:
        await current.startup()
    assert caught.value.error_code == DiErrorCodes.INVALID_LIFECYCLE


async def test_cancelled_shutdown_wait_keeps_thread_resolution_and_executor_exits(configuration):
    entered, release, destroyed = threading.Event(), threading.Event(), []

    @service
    class Resource:
        def pre_destroy(self):
            destroyed.append(True)

    @service(scope=ComponentScopeEnum.TRANSIENT)
    class Slow:
        def __init__(self):
            entered.set()
            assert release.wait(timeout=2)

    current = container([Resource, Slow], configuration)
    await current.startup()
    get_task = asyncio.create_task(asyncio.to_thread(current.get, Slow))
    assert await asyncio.to_thread(entered.wait, 1)
    closing = asyncio.create_task(current.shutdown())
    await asyncio.sleep(0.02)
    closing.cancel("调用方超时")
    with pytest.raises(asyncio.CancelledError):
        await closing
    # 取消的只是等待：线程内解析继续，容器停在 STOPPING，资源未销毁。
    assert current.state is ContainerStateEnum.STOPPING and not destroyed
    release.set()
    assert isinstance(await get_task, Slow)
    await current.shutdown()
    assert destroyed == [True] and current.state is ContainerStateEnum.CLOSED
    # Condition 等待的工作线程已返回，默认 executor 能在限时内关闭。
    await asyncio.wait_for(asyncio.get_running_loop().shutdown_default_executor(), timeout=2)
