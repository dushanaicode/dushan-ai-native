from dataclasses import replace
from importlib.resources import files

import pytest
from pydantic import ValidationError

from fixtures.config_factory import ConfigFactory
from framework.starter_web.banner import banner_application_runner
from framework.starter_web.banner.banner_application_runner import BannerApplicationRunner
from framework.starter_web.banner.banner_runtime_info import BannerRuntimeInfo
from framework.starter_web.banner.cat_mascot import CatMascotTUI
from framework.starter_web.config.banner_settings import BannerSettings

pytestmark = pytest.mark.unit


@pytest.fixture
def info():
    return BannerRuntimeInfo(
        app_name="示例应用",
        version="2.3.4",
        environment="dev",
        engine="granian",
        host="127.0.0.1",
        port=18080,
        root_path="/api",
        docs_url="/swagger",
        redoc_url="/reference",
        openapi_url="/schema.json",
        enabled_modules=(),
        disabled_modules=(),
    )


def runner(**overrides):
    return BannerApplicationRunner(ConfigFactory.build(BannerSettings, "banner", **overrides))


def test_enabled_banner_prints_all_reference_artwork(capsys):
    runner(show_worship=True).print_startup_banner()
    logo = (
        files("framework.starter_web.banner")
        .joinpath("assets/logo.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    captured = capsys.readouterr()
    worship = (
        files("framework.starter_web.banner")
        .joinpath("assets/worship.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert len(logo.split("\n\n")) == 3
    assert captured.out == logo + "\n" + worship + "\n"
    assert "_ooOoo_" in captured.out
    assert captured.err == ""


def test_worship_can_be_enabled_independently(capsys):
    runner(show_logo=False, show_worship=True).print_startup_banner()
    assert "_ooOoo_" in capsys.readouterr().out


def test_worship_can_be_disabled_without_trimming_the_logo(capsys):
    runner(show_worship=False).print_startup_banner()
    output = capsys.readouterr().out
    assert len(output.strip().split("\n\n")) == 3
    assert "_ooOoo_" not in output


async def test_disabled_banner_does_not_read_resources_or_emit_info(capsys, monkeypatch, info):
    def forbidden(*args):
        raise AssertionError("禁用时不应读取资源")

    monkeypatch.setattr(banner_application_runner, "files", forbidden)
    helper = runner(enabled=False, show_worship=True)
    helper.print_startup_banner()
    await helper.print_startup_complete(info)
    assert capsys.readouterr().out == ""


async def test_info_uses_actual_paths_and_optional_public_metadata(capsys, info):
    helper = runner(author="维护者", documentation_url="https://docs.example.com/guide")
    await helper.print_startup_complete(info)
    text = capsys.readouterr().out
    assert "示例应用" in text and "2.3.4" in text
    assert "Swagger：http://127.0.0.1:18080/api/swagger" in text
    assert "ReDoc：http://127.0.0.1:18080/api/reference" in text
    assert "OpenAPI：http://127.0.0.1:18080/api/schema.json" in text
    assert "https://docs.example.com/guide" in text and "维护者" in text
    assert "已启用模块" not in text and "未启用模块" not in text
    assert text.splitlines()[-3:] == [
        "引擎：granian",
        "环境：dev",
        "监听地址：http://127.0.0.1:18080",
    ]
    assert all(text.count(label) == 1 for label in ("引擎：", "环境：", "监听地址："))
    assert "访问地址：" not in text


@pytest.mark.parametrize(
    "host,expected", [("0.0.0.0", "127.0.0.1"), ("::", "[::1]"), ("2001:db8::1", "[2001:db8::1]")]
)
def test_wildcard_and_ipv6_addresses_have_usable_url_syntax(capsys, info, host, expected):
    runner().print_doc(replace(info, host=host))
    output = capsys.readouterr().out
    assert f"Swagger：http://{expected}:18080/api/swagger" in output
    assert output.count("监听地址：") == 1


def test_closed_docs_and_empty_author_do_not_show_false_links(capsys, info):
    runner(author="").print_doc(replace(info, docs_url=None, redoc_url=None, openapi_url=None))
    text = capsys.readouterr().out
    assert "接口文档：已关闭" in text
    assert all(
        label not in text for label in ("Swagger", "ReDoc", "OpenAPI", "作者：", "项目文档：")
    )


async def test_info_switch_and_explicit_module_lists(capsys, info):
    populated = replace(info, enabled_modules=("system",), disabled_modules=("bpm",))
    await runner(show_startup_info=False).print_startup_complete(populated)
    assert capsys.readouterr().out == ""
    await runner().print_startup_complete(populated)
    text = capsys.readouterr().out
    assert "[+] 已启用模块：system" in text
    assert "[-] 未启用模块：bpm" in text


def test_sensitive_text_does_not_escape_into_startup_output(capsys, info):
    runner(author="password=private-value").print_doc(info)
    assert "private-value" not in capsys.readouterr().out


def test_banner_settings_require_yaml_values_and_validate_public_url():
    with pytest.raises(ValidationError):
        BannerSettings()
    for url in ("bad-url", "https://user:password@example.com"):
        with pytest.raises(ValidationError):
            ConfigFactory.build(BannerSettings, "banner", documentation_url=url)


async def test_pytest_gate_keeps_plain_metadata_without_entering_animation(
    monkeypatch, capsys, info
):
    def forbidden(*args, **kwargs):
        pytest.fail("pytest 门禁不能进入动画渲染")

    monkeypatch.setattr(CatMascotTUI, "play_and_render_completion", forbidden)
    await runner().print_startup_complete(info)
    output = capsys.readouterr().out
    assert "\033" not in output
    assert all(output.count(label) == 1 for label in ("引擎：", "环境：", "监听地址："))


@pytest.mark.parametrize("show_mascot", [True, False])
async def test_regular_completion_keeps_all_links_bind_address_and_redaction(
    monkeypatch, capsys, info, show_mascot
):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    populated = replace(info, host="::", enabled_modules=("system",), disabled_modules=("bpm",))
    await runner(show_mascot=show_mascot, author="password=private-value").print_startup_complete(
        populated
    )
    output = capsys.readouterr().out
    assert "\033" not in output and "private-value" not in output
    assert all(
        f"http://[::1]:18080/api{path}" in output
        for path in ("/swagger", "/reference", "/schema.json")
    )
    assert "监听地址：http://[::]:18080" in output
    assert "system" in output and "未启用模块：bpm" in output
    assert "Lv.99" not in output


async def test_regular_completion_shows_disabled_documentation(monkeypatch, capsys, info):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    await runner().print_startup_complete(
        replace(info, docs_url=None, redoc_url=None, openapi_url=None)
    )
    output = capsys.readouterr().out
    assert "接口文档：已关闭" in output
    assert "Swagger" not in output and "ReDoc" not in output
