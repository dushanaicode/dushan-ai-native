import tomllib
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from pydantic import ValidationError

from framework.common.exception.exceptions.configuration_exception import ConfigurationException
from framework.common.importing.package_locator import PackageLocator
from framework.starter_module.module_definition import ModuleDefinition
from framework.starter_module.module_settings import ModuleSettings
from framework.starter_module.resolved_module import ResolvedModule


class ModuleLoader:
    """读取静态声明并验证启用依赖，不导入声明包或执行模块钩子。"""

    @classmethod
    def load(cls, settings: ModuleSettings) -> tuple[ResolvedModule, ...]:
        """全部声明验证成功后，按确定的依赖顺序返回启用模块。"""
        declarations: dict[str, ResolvedModule] = {}
        for package in sorted(settings.packages):
            root = PackageLocator.locate(package, package=True).parent
            definition = cls._read(root / "module.toml", package)
            if definition.name in declarations:
                raise ConfigurationException(msg=f"模块 ID 重复: {definition.name}")
            for existing in declarations.values():
                if root.is_relative_to(existing.root) or existing.root.is_relative_to(root):
                    raise ConfigurationException(
                        msg=f"模块物理范围重叠: {package} 与 {existing.definition.package}"
                    )
                if package.startswith(
                    existing.definition.package + "."
                ) or existing.definition.package.startswith(package + "."):
                    raise ConfigurationException(
                        msg=f"模块包范围重叠: {package} 与 {existing.definition.package}"
                    )
            declarations[definition.name] = ResolvedModule(definition, root)
        unknown = set(settings.enabled) - declarations.keys()
        if unknown:
            raise ConfigurationException(msg=f"启用模块未声明: {', '.join(sorted(unknown))}")
        graph = {}
        for name in sorted(settings.enabled):
            required = declarations[name].definition.requires
            missing = set(required) - set(settings.enabled)
            if missing:
                raise ConfigurationException(
                    msg=f"模块 {name} 的必要依赖未启用: {', '.join(sorted(missing))}"
                )
            graph[name] = sorted(required)
        try:
            order = tuple(TopologicalSorter(graph).static_order())
        except CycleError as error:
            raise ConfigurationException(
                msg="模块依赖存在循环: " + ", ".join(sorted(graph)), cause=error
            ) from error
        return tuple(declarations[name] for name in order)

    @staticmethod
    def _read(path: Path, package: str) -> ModuleDefinition:
        """声明错误带字段和文件来源，不把 TOML 的原始值输出到消息。"""
        try:
            if not path.resolve().is_relative_to(path.parent):
                raise ValueError("声明文件越出模块目录")
            definition = ModuleDefinition.model_validate(
                tomllib.loads(path.read_text(encoding="utf-8"))
            )
        except ValidationError as error:
            fields = ", ".join(
                ".".join(map(str, detail["loc"])) or "整体声明"
                for detail in error.errors(include_input=False, include_url=False)
            )
            raise ConfigurationException(
                msg=f"模块声明校验失败: {path}；字段: {fields}", cause=error
            ) from error
        except (OSError, ValueError) as error:
            raise ConfigurationException(
                msg=f"模块声明读取失败: {path} ({type(error).__name__})", cause=error
            ) from error
        if definition.package != package:
            raise ConfigurationException(
                msg=f"模块声明 package 与定位包不一致: {path}，预期 {package}"
            )
        return definition
