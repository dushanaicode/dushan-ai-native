import asyncio
import json
import threading
import traceback
import uuid
from pathlib import Path
from typing import Union

import pytest
import yaml
from pydantic import Field, field_validator

from fixtures.config_factory import ConfigFactory
from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorators.config_decorator import config_model
from framework.starter_config.definitions.enums.config_source_enum import ConfigSourceEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from framework.starter_config.provider.config_provider import ConfigProvider
from framework.starter_config.source.config_values import ConfigValues
from framework.starter_di.config.di_settings import DiSettings
from framework.starter_di.core.di_container import DiContainer
from framework.starter_di.decorators.components import service
from framework.starter_di.decorators.conditional import conditional

pytestmark = pytest.mark.unit


async def test_deferred_notification_task_can_refresh_after_callback_returns(config_dir):
    current = provider(config_dir)
    tasks = []

    async def later():
        await asyncio.sleep(0)
        return current.replace_memory({"config": {"models": {"sample": {"count": 6}}}})

    def listener(change):
        if not tasks:
            tasks.append(asyncio.create_task(later()))

    current.add_listener(listener)
    current.replace_memory({"config": {"models": {"sample": {"count": 5}}}})
    try:
        await tasks[0]
        assert current.get_config(SampleSettings).count == 6
    finally:
        current.close()


def test_identical_reload_does_not_advance_version_or_notify(config_dir):
    current = provider(config_dir)
    events = []
    current.add_listener(events.append)
    data = {"config": {"models": {"sample": {"count": 5}}}}
    first = current.replace_memory(data)
    second = current.replace_memory(data)
    assert second.change.revision == first.change.revision
    assert second.change.models == () and events == [first.change]
    current.close()


def test_masked_source_is_retained_without_spurious_model_notification(config_dir):
    current = provider(config_dir, environ={"SAMPLE_COUNT": "10"})
    events = []
    current.add_listener(events.append)
    result = current.replace_memory({"config": {"models": {"sample": {"count": 5}}}})
    assert result.change.models == () and current.revision == 2 and events == []
    assert current.get_config(SampleSettings).count == 10
    current.close()


def test_flat_file_restoring_null_parent_updates_group_source(config_dir, tmp_path):
    @config_model("tree", env_prefix="TREE_", field_keys={"value": "external"})
    class Settings(ConfigModel):
        value: dict[str, int]

    first, second = tmp_path / "null.yaml", tmp_path / "value.properties"
    first.write_text("external: null\n", encoding="utf-8")
    second.write_text("external.count=9\n", encoding="utf-8")
    root = config_dir(
        {
            "config": {
                "models": {},
                "files": [
                    {"path": str(first), "required": True},
                    {"path": str(second), "required": True},
                ],
            }
        }
    )
    current = ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Settings])
    assert current.get_config(Settings).value == {"count": 9}
    assert current.get_sources(Settings)["value"] == str(second)
    current.close()


def test_concurrent_notifications_are_ordered_and_reads_remain_available(config_dir):
    current = provider(config_dir)
    entered, release, second_done = threading.Event(), threading.Event(), threading.Event()
    seen, failures = [], []

    def listener(change):
        if change.revision == 2:
            entered.set()
            assert release.wait(2)
        seen.append((change.revision, current.revision))

    def change(count, done=None):
        try:
            current.replace_memory({"config": {"models": {"sample": {"count": count}}}})
        except BaseException as error:
            failures.append(error)
        finally:
            if done is not None:
                done.set()

    current.add_listener(listener)
    first = threading.Thread(target=change, args=(5,))
    second = threading.Thread(target=change, args=(6, second_done))
    first.start()
    assert entered.wait(1)
    second.start()
    second_done.wait(0.05)
    assert current.get_config(SampleSettings).count in {5, 6}
    release.set()
    first.join(2)
    second.join(2)
    assert not first.is_alive() and not second.is_alive() and failures == []
    assert seen == [(2, 2), (3, 3)]
    current.close()


@config_model("sample", env_prefix="SAMPLE_")
class SampleSettings(ConfigModel):
    enabled: bool
    count: int = Field(ge=0)
    names: list[str]
    optional: int | None
    password: str


def provider(config_dir, *, model=SampleSettings, environ=None, options=None):
    values = {
        "models": {
            "sample": {
                "enabled": True,
                "count": 4,
                "names": ["base"],
                "optional": 7,
                "password": "fixture-secret",
            }
        },
        "reload_enabled": True,
    }
    values.update({} if options is None else options)
    root = config_dir({"config": values})
    bootstrap = BootstrapConfigProvider.load(root, environ={} if environ is None else environ)
    return ConfigProvider(bootstrap, [model])


def test_config_model_sources_falsey_values_and_model_isolation(config_dir):
    current = provider(
        config_dir,
        environ={
            "SAMPLE_ENABLED": "false",
            "SAMPLE_COUNT": "0",
            "SAMPLE_NAMES": "[]",
            "SAMPLE_OPTIONAL": "null",
        },
    )
    model, sources, revision = current.read(SampleSettings)
    assert (model.enabled, model.count, model.names, model.optional) == (False, 0, [], None)
    assert sources["count"] == "环境变量 SAMPLE_COUNT" and revision == 1
    model.names.append("changed")
    assert current.get_config(SampleSettings).names == []
    assert "fixture-secret" not in json.dumps(current.export_values())
    assert current.get_sources(SampleSettings)["password"] == "application.yaml"


def test_snapshot_keeps_one_revision_after_live_refresh_and_close(config_dir):
    current = provider(config_dir)
    snapshot = current.snapshot()
    current.replace_memory({"config": {"models": {"sample": {"count": 9, "names": ["next"]}}}})
    model, sources, revision = snapshot.read(SampleSettings)
    assert model.count == 4 and revision == 1 and sources["count"] == "application.yaml"
    model.names.append("caller mutation")
    assert snapshot.get_config(SampleSettings).names == ["base"]
    assert current.get_config(SampleSettings).count == 9
    current.close()
    assert snapshot.get_config(SampleSettings).count == 4


async def test_di_conditions_share_a_snapshot_even_if_live_config_changes(config_dir):
    current = provider(config_dir)
    revisions = []

    def first_condition(snapshot):
        revisions.append(snapshot.revision)
        current.replace_memory({"config": {"models": {"sample": {"enabled": False}}}})
        return snapshot.get_config(SampleSettings).enabled

    @conditional(first_condition)
    @service
    class First:
        pass

    @conditional(lambda snapshot: snapshot.get_config(SampleSettings).enabled)
    @service
    class Second:
        pass

    container = DiContainer(
        [First, Second],
        configuration=current,
        settings=ConfigFactory.build(DiSettings, "di"),
        enabled_modules=frozenset(),
    )
    try:
        await container.startup()
        assert isinstance(container.get(First), First) and isinstance(container.get(Second), Second)
        assert revisions == [1] and current.revision == 2
        assert container.get_statistics()["configuration_revision"] == 1
    finally:
        await container.shutdown()
        current.close()


def test_model_and_field_source_order_and_explicit_key_mapping(config_dir):
    @config_model(
        "sample",
        env_prefix="SAMPLE_",
        sources=(ConfigSourceEnum.YAML,),
        field_sources={"count": (ConfigSourceEnum.MEMORY, ConfigSourceEnum.YAML)},
        field_keys={"enabled": "server.debug"},
    )
    class MappedSettings(SampleSettings):
        pass

    current = provider(config_dir, model=MappedSettings, environ={"SAMPLE_COUNT": "99"})
    current.replace_memory({"config": {"models": {"sample": {"count": 8}}}})
    value = current.get_config(MappedSettings)
    assert value.count == 8 and value.enabled is False
    assert current.get_sources(MappedSettings)["count"] == "内存配置覆盖"
    assert current.get_sources(MappedSettings)["enabled"] == "application.yaml"


def test_configuration_refresh_is_atomic_and_failed_updates_do_not_notify(config_dir):
    current = provider(config_dir)
    events = []
    current.add_listener(events.append)
    first = current.get_config(SampleSettings)
    with pytest.raises(BootstrapConfigError, match="count"):
        current.replace_memory({"config": {"models": {"sample": {"count": -1, "enabled": False}}}})
    assert current.revision == 1 and events == []
    assert current.get_config(SampleSettings) == first
    result = current.replace_memory(
        {"config": {"models": {"sample": {"count": 0, "enabled": False}}}}
    )
    assert result.change.models == ("sample",) and result.listener_errors == ()
    assert events == [result.change]
    assert current.get_config(SampleSettings).count == 0
    current.replace_memory({})
    assert current.get_config(SampleSettings).count == 4


def test_listener_failure_is_reported_without_lying_about_committed_state(config_dir):
    current = provider(config_dir)
    observed = []
    original = RuntimeError("listener failed")

    def bad_listener(change):
        raise original

    current.add_listener(bad_listener)
    current.add_listener(observed.append)
    result = current.replace_memory({"config": {"models": {"sample": {"count": 5}}}})
    assert result.listener_errors == (original,) and observed == [result.change]
    assert current.get_config(SampleSettings).count == 5
    assert current.remove_listener(bad_listener)


async def test_external_refresh_rejects_stale_results_and_preserves_cancellation(config_dir):
    current = provider(config_dir)
    entered, release = asyncio.Event(), asyncio.Event()

    async def loader():
        entered.set()
        await release.wait()
        return {"config": {"models": {"sample": {"count": 90}}}}

    task = asyncio.create_task(current.refresh_external(loader))
    await entered.wait()
    current.replace_memory({"config": {"models": {"sample": {"count": 3}}}})
    release.set()
    with pytest.raises(BootstrapConfigError, match="迟到"):
        await task
    assert current.get_config(SampleSettings).count == 3

    async def cancelled():
        raise asyncio.CancelledError("config cancellation")

    with pytest.raises(asyncio.CancelledError, match="config cancellation"):
        await current.refresh_external(cancelled)
    assert current.get_config(SampleSettings).count == 3


async def test_external_snapshot_is_a_real_source_with_original_failure(config_dir):
    current = provider(config_dir)

    async def loader():
        return {"config": {"models": {"sample": {"count": 9}}}}

    result = await current.refresh_external(loader)
    assert result.change.revision == 2 and current.get_config(SampleSettings).count == 9
    assert current.get_sources(SampleSettings)["count"] == "外部配置快照"

    async def unavailable():
        raise OSError("fixture failure")

    with pytest.raises(BootstrapConfigError) as caught:
        await current.refresh_external(unavailable)
    assert isinstance(caught.value.__cause__, OSError)
    assert current.revision == 2


@pytest.mark.parametrize(
    "suffix,content",
    [
        (".yaml", "config:\n  models:\n    sample:\n      count: 12\n"),
        (".json", '{"config":{"models":{"sample":{"count":12}}}}'),
        (".toml", "[config.models.sample]\ncount = 12\n"),
        (".ini", "[config.models.sample]\ncount = 12\n"),
        (".properties", "config.models.sample.count=12\n"),
    ],
)
def test_file_sources_formats_and_refresh_rollback(config_dir, tmp_path, suffix, content):
    path = tmp_path / ("override" + suffix)
    path.write_text(content, encoding="utf-8")
    current = provider(config_dir, options={"files": [{"path": str(path), "required": True}]})
    assert current.get_config(SampleSettings).count == 12
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(BootstrapConfigError):
        current.reload_files()
    assert current.get_config(SampleSettings).count == 12 and current.revision == 1


def test_nested_models_merge_files_and_environment_with_field_origins(config_dir, tmp_path):
    class Nested(ConfigModel):
        count: int
        enabled: bool

    @config_model("nested", env_prefix="NESTED_")
    class Settings(ConfigModel):
        child: Nested

    first, second = tmp_path / "first.yaml", tmp_path / "second.yaml"
    first.write_text(
        "config:\n  models:\n    nested:\n      child:\n        count: 10\n        enabled: true\n",
        encoding="utf-8",
    )
    second.write_text(
        "config:\n  models:\n    nested:\n      child:\n        count: 20\n", encoding="utf-8"
    )
    root = config_dir(
        {
            "config": {
                "models": {},
                "files": [
                    {"path": str(first), "required": True},
                    {"path": str(second), "required": True},
                ],
            }
        }
    )
    current = ConfigProvider(
        BootstrapConfigProvider.load(root, environ={"NESTED_CHILD_ENABLED": "false"}), [Settings]
    )
    assert current.get_config(Settings).child.count == 20
    assert current.get_config(Settings).child.enabled is False
    sources = current.get_sources(Settings)
    assert sources["child.count"] == str(second)
    assert sources["child.enabled"] == "环境变量 NESTED_CHILD_ENABLED"


@pytest.mark.parametrize(
    "case",
    ["missing", "unknown_field", "unknown_environment", "duplicate_model", "default_in_model"],
)
def test_invalid_model_contracts_fail_without_private_values(config_dir, case):
    if case == "default_in_model":

        @config_model("defaults", env_prefix="DEFAULTS_")
        class Bad(ConfigModel):
            count: int = 2

        with pytest.raises(BootstrapConfigError, match="公共 YAML"):
            provider(config_dir, model=Bad)
        return
    if case == "unknown_environment":
        with pytest.raises(BootstrapConfigError, match="SAMPLE_COUNTT") as caught:
            provider(config_dir, environ={"SAMPLE_COUNTT": "private-value"})
        assert "private-value" not in str(caught.value)
        return
    root = config_dir(
        {
            "config": {
                "models": {
                    "sample": {
                        "enabled": True,
                        "count": 4,
                        "names": [],
                        "optional": None,
                        "password": "private-value",
                    }
                }
            }
        }
    )
    if case == "duplicate_model":

        @config_model("sample", env_prefix="OTHER_")
        class Other(SampleSettings):
            pass

        classes = [SampleSettings, Other]
    else:
        path = root / "application.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if case == "missing":
            del raw["config"]["models"]["sample"]["count"]
        else:
            raw["config"]["models"]["sample"]["unknown"] = "private-value"
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        classes = [SampleSettings]
    with pytest.raises(BootstrapConfigError) as caught:
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), classes)
    assert "private-value" not in str(caught.value)


def test_reload_off_closed_and_unselected_file_have_real_effect(config_dir, tmp_path):
    current = provider(
        config_dir,
        options={
            "reload_enabled": False,
            "source_order": ["yaml"],
            "files": [{"path": str(tmp_path / "absent.yaml"), "required": True}],
        },
    )
    with pytest.raises(BootstrapConfigError, match="关闭"):
        current.replace_memory({})
    assert current.get_config(SampleSettings).count == 4
    current.close()
    with pytest.raises(BootstrapConfigError, match="已关闭"):
        current.get_config(SampleSettings)


def test_empty_dictionary_override_is_preserved_and_flat_files_update_nested_models(
    config_dir, tmp_path
):
    class Child(ConfigModel):
        count: int
        enabled: bool

    @config_model("data", env_prefix="DATA_")
    class Settings(ConfigModel):
        mapping: dict[str, int]
        child: Child

    first, second = tmp_path / "first.yaml", tmp_path / "second.properties"
    first.write_text(
        "config:\n  models:\n    data:\n      child:\n        count: 5\n        enabled: true\n",
        encoding="utf-8",
    )
    second.write_text("config.models.data.child.count=6\n", encoding="utf-8")
    root = config_dir(
        {
            "config": {
                "models": {"data": {"mapping": {"a": 1}}},
                "files": [
                    {"path": str(first), "required": True},
                    {"path": str(second), "required": True},
                ],
            }
        }
    )
    current = ConfigProvider(
        BootstrapConfigProvider.load(root, environ={"DATA_MAPPING": "{}"}), [Settings]
    )
    assert current.get_config(Settings).mapping == {}
    assert current.get_config(Settings).child.count == 6
    assert current.get_config(Settings).child.enabled is True


def test_notifications_do_not_allow_recursive_config_writes_or_hide_cancellation(config_dir):
    current = provider(config_dir)

    def recursive(change):
        current.replace_memory({})

    current.add_listener(recursive)
    result = current.replace_memory({"config": {"models": {"sample": {"count": 5}}}})
    assert isinstance(result.listener_errors[0], BootstrapConfigError)
    assert current.revision == 2
    current.remove_listener(recursive)

    def cancelled(change):
        raise asyncio.CancelledError("listener cancelled")

    current.add_listener(cancelled)
    with pytest.raises(asyncio.CancelledError, match="listener cancelled"):
        current.replace_memory({})
    assert current.get_config(SampleSettings).count == 4


def test_parent_null_does_not_leave_stale_mapped_children_in_file_layers(config_dir, tmp_path):
    @config_model("mapped", env_prefix="MAPPED_", field_keys={"value": "external.child.count"})
    class Settings(ConfigModel):
        value: int

    first, second = tmp_path / "first.yaml", tmp_path / "second.yaml"
    first.write_text("external:\n  child:\n    count: 9\n", encoding="utf-8")
    second.write_text("external:\n  child: null\n", encoding="utf-8")
    root = config_dir(
        {
            "config": {
                "files": [
                    {"path": str(first), "required": True},
                    {"path": str(second), "required": True},
                ]
            }
        }
    )
    with pytest.raises(BootstrapConfigError, match="value"):
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Settings])


async def test_disabled_external_source_does_not_call_loader(config_dir):
    current = provider(config_dir, options={"source_order": ["yaml"]})

    async def forbidden():
        pytest.fail("未启用的外部源不能执行 I/O")

    with pytest.raises(BootstrapConfigError, match="source_order"):
        await current.refresh_external(forbidden)


def test_file_reload_rejects_a_snapshot_if_another_update_was_published(config_dir, monkeypatch):
    current = provider(config_dir)

    def concurrent_read():
        current.replace_memory({"config": {"models": {"sample": {"count": 6}}}})
        return {}, {}

    monkeypatch.setattr(current, "_read_files", concurrent_read)
    with pytest.raises(BootstrapConfigError, match="迟到快照"):
        current.reload_files()
    assert current.get_config(SampleSettings).count == 6


def test_environment_name_ambiguity_inside_a_model_fails_at_declaration(config_dir):
    class Child(ConfigModel):
        b: int

    @config_model("ambiguous", env_prefix="AMBIGUOUS_")
    class Ambiguous(ConfigModel):
        a_b: int
        a: Child

    root = config_dir({"config": {"models": {"ambiguous": {"a_b": 1, "a": {"b": 2}}}}})
    with pytest.raises(BootstrapConfigError, match="AMBIGUOUS_A_B") as caught:
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Ambiguous])
    assert "a_b" in str(caught.value) and "a.b" in str(caught.value)


def test_model_prefixes_must_not_repeat_or_nest_each_other(config_dir):
    @config_model("outer", env_prefix="X_")
    class Outer(ConfigModel):
        a: int

    @config_model("inner", env_prefix="X_A_")
    class Inner(ConfigModel):
        b: int

    @config_model("twin", env_prefix="X_")
    class Twin(ConfigModel):
        c: int

    @config_model("apart", env_prefix="XA_")
    class Apart(ConfigModel):
        d: int

    models = {"outer": {"a": 1}, "inner": {"b": 2}, "twin": {"c": 3}, "apart": {"d": 4}}
    bootstrap = BootstrapConfigProvider.load(
        config_dir({"config": {"models": models}}), environ={"X_A": "5"}
    )
    for classes, names in (
        ([Outer, Inner], ("outer", "inner")),
        ([Inner, Outer], ("inner", "outer")),
        ([Outer, Twin], ("outer", "twin")),
    ):
        with pytest.raises(BootstrapConfigError, match="配置模型环境前缀重叠") as caught:
            ConfigProvider(bootstrap, classes)
        assert all(name in str(caught.value) for name in names)
    current = ConfigProvider(bootstrap, [Outer, Apart])
    assert (current.get_config(Outer).a, current.get_config(Apart).d) == (5, 4)
    current.close()


@pytest.mark.parametrize("prefix", ["LOG_", "LOG_FILE_"])
def test_model_prefix_cannot_overlap_a_bootstrap_group(config_dir, prefix):
    @config_model("log_extra", env_prefix=prefix)
    class Extra(ConfigModel):
        value: int

    root = config_dir({"config": {"models": {"log_extra": {"value": 1}}}})
    with pytest.raises(BootstrapConfigError, match=r"启动配置分组 log \(LOG_\)") as caught:
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Extra])
    assert prefix in str(caught.value)


def test_validation_failure_keeps_values_out_of_message_and_traceback(config_dir):
    marker = f"marker-{uuid.uuid4().hex}"
    current = provider(config_dir)
    events = []
    current.add_listener(events.append)
    before = current.read(SampleSettings)
    with pytest.raises(BootstrapConfigError) as caught:
        current.replace_memory({"config": {"models": {"sample": {"count": marker}}}})
    rendered = "".join(traceback.format_exception(caught.value))
    assert marker not in rendered
    assert "config.models.sample.count" in str(caught.value) and "int_parsing" in str(caught.value)
    assert "内存配置覆盖" in str(caught.value)
    assert current.read(SampleSettings) == before and events == []
    current.close()


def test_custom_validator_text_with_input_stays_out_of_normal_output(config_dir):
    marker = f"marker-{uuid.uuid4().hex}"

    @config_model("guarded", env_prefix="GUARDED_")
    class Guarded(ConfigModel):
        token: str

        @field_validator("token")
        @classmethod
        def reject_marked_token(cls, value: str) -> str:
            if value.startswith("marker-"):
                raise ValueError(f"不允许的令牌 {value}")
            return value

    root = config_dir({"config": {"models": {"guarded": {"token": marker}}}})
    with pytest.raises(BootstrapConfigError) as caught:
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Guarded])
    rendered = "".join(traceback.format_exception(caught.value))
    assert marker not in rendered
    assert "config.models.guarded.token" in str(caught.value) and "value_error" in str(caught.value)


@pytest.mark.parametrize("suffix", [".ini", ".yaml"])
def test_broken_additional_file_does_not_echo_its_content(config_dir, tmp_path, suffix):
    # YAML 的错误片段只展示出错位置附近的内容，标记保持较短才能证明片段确实会被带出。
    marker = f"marker-{uuid.uuid4().hex[:12]}"
    path = tmp_path / f"broken{suffix}"
    content = f"[config]\n{marker}\n" if suffix == ".ini" else f'count: "{marker}\nnext: 1\n'
    path.write_text(content, encoding="utf-8")
    root = config_dir({"config": {"files": [{"path": str(path), "required": True}]}})
    with pytest.raises(BootstrapConfigError, match="配置文件读取失败") as caught:
        ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [])
    assert marker not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("raw, expected", [(' {"value": 7}', 7), ("null", None)])
def test_optional_nested_model_environment_json(config_dir, raw, expected):
    class Child(ConfigModel):
        value: int

    @config_model("optional_child", env_prefix="OPTIONAL_CHILD_")
    class Settings(ConfigModel):
        child: Child | None

    root = config_dir({"config": {"models": {"optional_child": {"child": None}}}})
    bootstrap = BootstrapConfigProvider.load(root, environ={"OPTIONAL_CHILD_CHILD": raw})
    current = ConfigProvider(bootstrap, [Settings])
    try:
        child = current.get_config(Settings).child
        assert (None if child is None else child.value) == expected
    finally:
        current.close()


@pytest.mark.parametrize("union_style", ["pipe", "typing"])
@pytest.mark.parametrize("labels", [{"region": "test"}, {}])
def test_optional_nested_model_replaces_dictionary_and_clears_sources(
    config_dir, union_style, labels
):
    """可空模型逐字段合并，普通字典覆盖同时移除旧键及其来源。"""

    class Child(ConfigModel):
        labels: dict[str, str]
        limit: int

    child_type = Child | None if union_style == "pipe" else Union[Child, None]

    class Branch(ConfigModel):
        child: child_type

    @config_model("optional_tree", env_prefix="OPTIONAL_TREE_")
    class Settings(ConfigModel):
        child: child_type
        branch: Branch | None

    child = {"labels": {"region": "demo", "zone": "a"}, "limit": 3}
    root = config_dir(
        {
            "config": {
                "models": {"optional_tree": {"child": child, "branch": {"child": child}}},
                "reload_enabled": True,
            }
        }
    )
    current = ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Settings])
    try:
        current.replace_memory(
            {
                "config.models.optional_tree.child.labels": labels,
                "config.models.optional_tree.branch.child.labels": labels,
            }
        )
        settings = current.get_config(Settings)
        assert settings.child.labels == settings.branch.child.labels == labels
        assert settings.child.limit == settings.branch.child.limit == 3
        sources = current.get_sources(Settings)
        for path in ("child", "branch.child"):
            assert sources[f"{path}.labels"] == "内存配置覆盖"
            assert sources[f"{path}.limit"] == "application.yaml"
            assert {name for name in sources if name.startswith(f"{path}.labels.")} == {
                f"{path}.labels.{name}" for name in labels
            }
        current.replace_memory({"config.models.optional_tree.child": None})
        assert current.get_config(Settings).child is None
        assert not any(name.startswith("child.") for name in current.get_sources(Settings))
    finally:
        current.close()


def test_multiple_model_union_retains_existing_merge_semantics(config_dir):
    """本次可空模型修复不改变多模型联合字段的映射合并合同。"""

    class First(ConfigModel):
        labels: dict[str, str]

    class Second(ConfigModel):
        value: int

    @config_model("model_union", env_prefix="MODEL_UNION_")
    class Settings(ConfigModel):
        child: First | Second

    root = config_dir(
        {
            "config": {
                "models": {"model_union": {"child": {"labels": {"old": "value"}}}},
                "reload_enabled": True,
            }
        }
    )
    current = ConfigProvider(BootstrapConfigProvider.load(root, environ={}), [Settings])
    try:
        current.replace_memory({"config.models.model_union.child.labels": {"new": "value"}})
        assert current.get_config(Settings).child.labels == {"old": "value", "new": "value"}
    finally:
        current.close()


@pytest.mark.parametrize("source", ["environment", "memory"])
def test_malformed_collection_json_does_not_echo_input(config_dir, source):
    """环境与内存集合的 JSON 错误不在异常链中暴露原始输入。"""
    marker = f"marker-{uuid.uuid4().hex}"
    raw = f'["{marker}"'
    if source == "environment":
        with pytest.raises(BootstrapConfigError) as caught:
            provider(config_dir, environ={"SAMPLE_NAMES": raw})
    else:
        current = provider(config_dir)
        try:
            before = current.read(SampleSettings)
            with pytest.raises(BootstrapConfigError) as caught:
                current.replace_memory({"config.models.sample.names": raw})
            assert current.read(SampleSettings) == before
        finally:
            current.close()
    assert "names" in str(caught.value)
    assert marker not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__suppress_context__


def test_model_union_with_string_keeps_environment_string(config_dir):
    class Child(ConfigModel):
        value: int

    @config_model("string_child", env_prefix="STRING_CHILD_")
    class Settings(ConfigModel):
        child: Child | str | None

    root = config_dir({"config": {"models": {"string_child": {"child": None}}}})
    current = ConfigProvider(
        BootstrapConfigProvider.load(root, environ={"STRING_CHILD_CHILD": "null"}), [Settings]
    )
    try:
        assert current.get_config(Settings).child == "null"
    finally:
        current.close()


def test_bootstrap_validator_does_not_echo_input(config_dir):
    marker = f"marker-{uuid.uuid4().hex}"

    class Guarded(ConfigModel):
        token: str

        @field_validator("token")
        @classmethod
        def reject(cls, value):
            raise ValueError(f"不允许的令牌 {value}")

    bootstrap = BootstrapConfigProvider.load(config_dir({"guarded": {"token": marker}}), environ={})
    with pytest.raises(BootstrapConfigError, match="value_error") as caught:
        bootstrap.get_config(Guarded, prefix="GUARDED_")
    assert marker not in "".join(traceback.format_exception(caught.value))


def test_closed_provider_rejects_listener_removal(config_dir):
    current = provider(config_dir)
    current.close()
    with pytest.raises(BootstrapConfigError, match="已关闭"):
        current.remove_listener(lambda change: None)


def test_unresolved_model_annotation_is_a_configuration_error(config_dir):
    @config_model("unresolved", env_prefix="UNRESOLVED_")
    class Unresolved(ConfigModel):
        child: "MissingConfigurationChild"  # noqa: F821

    with pytest.raises(BootstrapConfigError, match="未解析的类型注解"):
        ConfigProvider(BootstrapConfigProvider.load(config_dir(), environ={}), [Unresolved])


@pytest.mark.parametrize("source", ["environment", "memory"])
@pytest.mark.parametrize(
    "field, raw, expected",
    [
        ("numbers", "[]", []),
        ("numbers", "[0, 7]", [0, 7]),
        ("mapping", "{}", {}),
        ("mapping", '{"next": 0}', {"next": 0}),
        ("model_mapping", "{}", {}),
        ("model_mapping", '{"next": {"value": 0}}', {"next": {"value": 0}}),
        ("optional", "null", None),
        ("model", '{"value": 7}', {"value": 7}),
        ("text", "null", "null"),
        ("text", '{"value": 7}', '{"value": 7}'),
    ],
)
def test_declared_nested_environment_json(source, field, raw, expected):
    class Leaf(ConfigModel):
        value: int

    class Child(ConfigModel):
        numbers: list[int]
        mapping: dict[str, int]
        model_mapping: dict[str, Leaf]
        optional: int | None
        model: Leaf | None
        text: Leaf | str | None

    @config_model("nested_json", env_prefix="NESTED_JSON_")
    class Settings(ConfigModel):
        child: Child

    values = ConfigFactory.values()
    values["config"]["reload_enabled"] = True
    values["config"]["models"] = {
        "nested_json": {
            "child": {
                "numbers": [1],
                "mapping": {"base": 1},
                "model_mapping": {"base": {"value": 1}},
                "optional": 1,
                "model": None,
                "text": None,
            }
        }
    }
    variable = f"NESTED_JSON_CHILD_{field.upper()}"
    bootstrap = BootstrapConfigProvider(
        Path.cwd(),
        ApplicationEnvironmentEnum.DEVELOPMENT,
        values,
        {variable: raw} if source == "environment" else {},
        ConfigValues.sources(values, "application.yaml"),
        ("application.yaml",),
    )
    current = ConfigProvider(bootstrap, [Settings])
    try:
        if source == "memory":
            override = raw if field == "text" else json.loads(raw)
            current.replace_memory(
                {"config": {"models": {"nested_json": {"child": {field: override}}}}}
            )
        child = current.get_config(Settings).child.model_dump()
        assert child[field] == expected
        sources = current.get_sources(Settings)
        assert sources[f"child.{field}"] == (
            f"环境变量 {variable}" if source == "environment" else "内存配置覆盖"
        )
        if field in {"mapping", "model_mapping"}:
            assert not any(name.startswith(f"child.{field}.base") for name in sources)
        assert child["numbers"] == (expected if field == "numbers" else [1])
    finally:
        current.close()
