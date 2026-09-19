import pytest
from pydantic import ValidationError

from fixtures.cache_fixtures import cache_settings
from framework.starter_cache.core.cache_key_registry import CacheKeyRegistry
from framework.starter_cache.core.cache_key_resolver import CacheKeyResolver
from framework.starter_cache.exception.cache_exception import CacheException
from framework.starter_cache.model.cache_key import CacheKey
from framework.starter_cache.model.cache_key_container import CacheKeyContainer

pytestmark = pytest.mark.unit


def container(**members) -> type[CacheKeyContainer]:
    """按成员声明生成一个真实容器类。"""
    return type("GeneratedKeys", (CacheKeyContainer,), members)


def key(name: str, **overrides) -> CacheKey:
    values = {"key": name, "remark": "测试键", "client_name": "default"}
    values.update(overrides)
    return CacheKey(**values)


def settings(**overrides):
    return cache_settings(
        clients=[{"name": "default", "db": 0}, {"name": "second", "db": 1}], **overrides
    )


def test_container_collects_declared_keys_from_itself_and_base_classes():
    base = container(A=key("a"))
    child = type("ChildKeys", (base,), {"B": key("b")})

    assert [item.key for item in child.declared_keys()] == ["a", "b"]


def test_registry_accepts_a_valid_declaration_set():
    registry = CacheKeyRegistry()
    registry.register([container(A=key("a"), B=key("b", client_name="second"))], settings())

    assert registry.is_registered is True
    assert sorted(registry.get_all()) == ["a", "b"]
    assert registry.find("a").client_name == "default"
    assert registry.find("missing") is None


def test_registry_tolerates_an_application_without_any_declared_key():
    registry = CacheKeyRegistry()
    registry.register([], settings())

    assert registry.is_registered is True and registry.get_all() == {}


def test_registry_rejects_duplicate_prefix_across_containers():
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="重复声明"):
        registry.register([container(A=key("a")), container(B=key("a"))], settings())


@pytest.mark.parametrize("other", ["a:b", "a:b:c"])
def test_registry_rejects_prefixes_that_contain_each_other(other):
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="互相包含"):
        registry.register([container(A=key("a"), B=key(other))], settings())


def test_registry_rejects_keys_pointing_at_an_unconfigured_client():
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="未配置的客户端"):
        registry.register([container(A=key("a", client_name="absent"))], settings())


def test_registry_rejects_colocation_group_split_across_clients():
    declaration = container(
        A=key("a", colocation_group="session"),
        B=key("b", client_name="second", colocation_group="session"),
    )
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="共置组路由不一致"):
        registry.register([declaration], settings())


def test_registry_accepts_colocation_group_on_one_client():
    registry = CacheKeyRegistry()
    registry.register(
        [container(A=key("a", colocation_group="session"), B=key("b", colocation_group="session"))],
        settings(),
    )
    assert sorted(registry.get_all()) == ["a", "b"]


def test_registry_refuses_to_register_twice():
    registry = CacheKeyRegistry()
    registry.register([], settings())
    with pytest.raises(CacheException, match="不能重复登记"):
        registry.register([], settings())


def test_registry_validates_application_resource_keys_with_static_keys():
    registry = CacheKeyRegistry()
    resource = key("captcha", client_name="second")
    registry.register([container(A=key("a"))], settings(), resource_keys=[resource])
    assert registry.find("captcha") is resource
    assert set(registry.get_all()) == {"a", "captcha"}


@pytest.mark.parametrize("name", ["a", "a:b"])
def test_resource_keys_cannot_overlap_static_keys(name):
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="重复声明|互相包含"):
        registry.register([container(A=key("a"))], settings(), resource_keys=[key(name)])
    assert not registry.is_registered and not registry.get_all()


def test_resource_keys_cannot_reference_unconfigured_clients():
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="未配置的客户端"):
        registry.register([], settings(), resource_keys=[key("a", client_name="absent")])


def test_resource_keys_must_obey_colocation_with_static_keys():
    registry = CacheKeyRegistry()
    with pytest.raises(CacheException, match="共置组路由不一致"):
        registry.register(
            [container(A=key("a", colocation_group="session"))],
            settings(),
            resource_keys=[key("b", client_name="second", colocation_group="session")],
        )


@pytest.mark.parametrize("name", ["Abc", "9abc", "a-b", "a:", ":a", "a::b", "a b", "", "a" * 129])
def test_cache_key_prefix_pattern_rejects_unsafe_names(name):
    with pytest.raises(ValidationError):
        key(name)


@pytest.mark.parametrize("name", ["a", "a_b", "a:b", "a1:b2:c3"])
def test_cache_key_prefix_pattern_accepts_segmented_lowercase_names(name):
    assert key(name).key == name


def test_cache_key_rejects_non_positive_default_ttl():
    with pytest.raises(ValidationError):
        key("a", default_ttl_seconds=0)


def test_resolver_builds_physical_key_and_prefix_pattern():
    cache_key = key("role")
    assert CacheKeyResolver.build_full_key(cache_key, "42") == "role:42"
    assert CacheKeyResolver.build_prefix_pattern(cache_key) == "role:*"


def test_settings_reject_default_client_that_is_not_declared():
    with pytest.raises(ValidationError, match="默认 Redis 客户端未声明"):
        cache_settings(clients=[{"name": "default", "db": 0}], default_client="absent")


def test_settings_reject_duplicate_client_names():
    with pytest.raises(ValidationError, match="不能重复"):
        cache_settings(clients=[{"name": "default", "db": 0}, {"name": "default", "db": 1}])


def test_settings_reject_username_without_password():
    with pytest.raises(ValidationError, match="必须与密码同时配置"):
        cache_settings(username="app", password=None)


def test_settings_reject_null_ttl_longer_than_max_ttl():
    with pytest.raises(ValidationError, match="不能超过 max_ttl_seconds"):
        cache_settings(max_ttl_seconds=30, null_value_ttl_seconds=60)


def test_settings_require_at_least_one_client_when_enabled():
    with pytest.raises(ValidationError, match="至少声明一个"):
        cache_settings(clients=[])
