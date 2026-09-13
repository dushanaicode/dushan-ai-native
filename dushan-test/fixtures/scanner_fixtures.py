import json
import sys

import pytest


@pytest.fixture
def module_package(tmp_path, monkeypatch):
    """在 pytest 的受控 Temp 中生成真实包、TOML 和语言资源。"""
    monkeypatch.syspath_prepend(str(tmp_path))
    packages = []

    def create(
        package,
        *,
        name=None,
        files=None,
        scan_roots=(".",),
        definitions=(),
        requires=(),
        messages=None,
        required_keys=(),
    ):
        packages.append(package.split(".")[0])
        root = tmp_path.joinpath(*package.split("."))
        root.mkdir(parents=True, exist_ok=True)
        parent = root
        while parent != tmp_path:
            (parent / "__init__.py").touch()
            parent = parent.parent
        for relative, source in (files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == ".py":
                parent = target.parent
                while parent != root:
                    (parent / "__init__.py").touch()
                    parent = parent.parent
            target.write_text(source, encoding="utf-8")
        declaration = (
            f"name = {json.dumps(package if name is None else name)}\n"
            f"package = {json.dumps(package)}\n"
            f"scan_roots = {json.dumps(scan_roots)}\n"
            f"definitions = {json.dumps(definitions)}\n"
            f"requires = {json.dumps(requires)}\n"
            f"required_message_keys = {json.dumps(required_keys)}\n"
        )
        if messages is None:
            declaration += "resource_roots = []\n"
        else:
            resources = root / "definitions/i18n"
            resources.mkdir(parents=True, exist_ok=True)
            for locale in ("zh-CN", "en-US"):
                (resources / f"{locale}.json").write_text(
                    json.dumps(messages[locale], ensure_ascii=False), encoding="utf-8"
                )
            declaration += f'[[resource_roots]]\npath = "definitions/i18n"\nscope = {json.dumps(package if name is None else name)}\nrequired = true\n'
        (root / "module.toml").write_text(declaration, encoding="utf-8")
        return root

    yield create
    for name in tuple(sys.modules):
        if any(name == package or name.startswith(package + ".") for package in packages):
            del sys.modules[name]


def error_source(name, code, key):
    """生成可被真实导入、注册和翻译的错误定义。"""
    return (
        "from framework.common.exception.core.error_code import ErrorCode\n"
        "from framework.common.exception.registry.error_code_decorator import error_code\n"
        f"@error_code\nclass {name}:\n"
        f"    FAILURE = ErrorCode(code={code}, description='模块错误', message_key={key!r})\n"
    )
