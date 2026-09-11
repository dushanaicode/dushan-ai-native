import pytest

from framework.common.exception.core.error_code import ErrorCode
from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.exception.registry.error_code_registry import ErrorCodeRegistry

pytestmark = pytest.mark.unit


def test_registry_instances_keep_their_own_code_definitions():
    """相同编号在两个独立应用目录中可以各自解析，不互相覆盖。"""

    class FirstCodes:
        FAILURE = ErrorCode(code=1000, description="第一个应用", message_key="first.failure")

    class SecondCodes:
        FAILURE = ErrorCode(code=1000, description="第二个应用", message_key="second.failure")

    first = ErrorCodeRegistry([FirstCodes])
    second = ErrorCodeRegistry([SecondCodes])
    assert first.get_by_code(1000) is FirstCodes.FAILURE
    assert second.get_by_code(1000) is SecondCodes.FAILURE
    assert first.get_by_code(9999) is None


def test_failed_construction_preserves_existing_registry_and_reports_both_sources():
    """后段冲突不破坏已用目录，同名类的诊断仍能区分模块来源。"""
    first_code = ErrorCode(code=1000, description="原定义", message_key="first.failure")
    first_class = type("Codes", (), {"__module__": "example.first", "FAILURE": first_code})
    second_class = type(
        "Codes",
        (),
        {
            "__module__": "example.second",
            "A_VALID": ErrorCode(code=1001, description="较早收集", message_key="second.valid"),
            "Z_CONFLICT": ErrorCode(
                code=1000, description="编号冲突", message_key="second.failure"
            ),
        },
    )
    existing = ErrorCodeRegistry([first_class])
    before = existing.get_all_detail()
    with pytest.raises(ConfigurationException) as caught:
        ErrorCodeRegistry([first_class, second_class])
    assert "1000" in caught.value.msg
    assert "example.first.Codes.FAILURE" in caught.value.msg
    assert "example.second.Codes.Z_CONFLICT" in caught.value.msg
    assert existing.get_all_detail() == before
    assert existing.get_by_code(1001) is None


@pytest.mark.parametrize("repeat_class", [False, True])
def test_duplicate_codes_are_not_silently_deduplicated(repeat_class):
    """重复来源类或同一类的同码别名都明确拒绝。"""
    code = ErrorCode(code=1000, description="重复编号", message_key="duplicate.code")

    class Codes:
        FIRST = code

    if repeat_class:
        sources = [Codes, Codes]
    else:
        Codes.SECOND = code
        sources = [Codes]
    with pytest.raises(ConfigurationException, match="1000"):
        ErrorCodeRegistry(sources)


def test_query_collections_cannot_mutate_the_internal_registry():
    """调用方修改两种查询副本，不会影响后续查询。"""

    class Codes:
        FAILURE = ErrorCode(code=1000, description="原定义", message_key="failure")

    registry = ErrorCodeRegistry([Codes])
    all_codes = registry.get_all()
    details = registry.get_all_detail()
    all_codes.clear()
    details[1000] = ("changed", "changed", Codes.FAILURE)
    assert registry.get_by_code(1000) is Codes.FAILURE
    assert registry.get_all_detail()[1000] == (
        f"{Codes.__module__}.{Codes.__qualname__}",
        "FAILURE",
        Codes.FAILURE,
    )


def test_static_collection_keeps_inherited_constants_without_executing_descriptors():
    """保留继承常量，并跳过私有值、普通字段及未求值的描述符。"""

    class Descriptor:
        def __get__(self, instance, owner):
            raise AssertionError("注册错误码不应执行描述符")

    class ParentCodes:
        SHARED = ErrorCode(code=1000, description="继承定义", message_key="shared")
        _PRIVATE = ErrorCode(code=1001, description="私有定义", message_key="private")

    class ChildCodes(ParentCodes):
        DESCRIPTION = "不是错误码"
        DYNAMIC = Descriptor()

    registry = ErrorCodeRegistry([ChildCodes])
    assert registry.get_all() == {1000: ParentCodes.SHARED}


def test_empty_and_iterable_sources_create_complete_independent_catalogs():
    """接受明确空目录与一次性迭代器，构建后不再依赖来源列表。"""
    empty = ErrorCodeRegistry([])
    assert empty.get_all() == {} and empty.get_all_detail() == {}
    assert empty.get_by_code(1000) is None

    class Codes:
        FAILURE = ErrorCode(code=1000, description="定义", message_key="failure")

    source = [Codes]
    registry = ErrorCodeRegistry(iter(source))
    source.clear()
    assert registry.get_by_code(1000) is Codes.FAILURE
