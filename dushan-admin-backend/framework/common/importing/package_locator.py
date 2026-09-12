import importlib
import keyword
import sys
from importlib.machinery import PathFinder, SourceFileLoader
from pathlib import Path
from types import ModuleType

from framework.common.exception.exceptions.configuration_exception import ConfigurationException


class PackageLocator:
    """在现有导入路径中定位普通 Python 源包，不为查找子包而执行父包。

    支持磁盘源码与已解包安装的 wheel，不修改 sys.path，不支持 namespace/zip 包。
    导入前检查已载入父包和候选文件，导入后再次核对；这不是任意 Python 的沙箱。
    """

    @staticmethod
    def is_valid_name(name: str) -> bool:
        """检查完整点分名称，排除 Python 关键字。"""
        return bool(name) and all(
            part.isidentifier() and not keyword.iskeyword(part) for part in name.split(".")
        )

    @classmethod
    def locate(cls, name: str, *, package: bool = False) -> Path:
        """逐级定位唯一源码，拒绝同名多来源以及被改写的包搜索路径。"""
        if not cls.is_valid_name(name):
            raise ConfigurationException(msg=f"非法 Python 包/模块名称: {name}")
        search_paths = list(sys.path)
        parts = name.split(".")
        parent: Path | None = None
        for index in range(len(parts)):
            prefix = ".".join(parts[: index + 1])
            origins: set[Path] = set()
            for entry in search_paths:
                spec = PathFinder.find_spec(prefix, [entry])
                if spec is None:
                    continue
                # 正常包会遮蔽同名 namespace 目录；测试目录也可能贡献这种目录。
                if spec.loader is None and spec.origin is None:
                    continue
                if not isinstance(spec.loader, SourceFileLoader) or spec.origin is None:
                    raise ConfigurationException(msg=f"仅支持磁盘普通 Python 源包: {prefix}")
                source = Path(spec.origin)
                if source.is_symlink() or source.parent.is_symlink() or source.parent.is_junction():
                    raise ConfigurationException(
                        msg=f"包/模块来源不允许链接或目录联接: {prefix} ({source})"
                    )
                origins.add(source.resolve(strict=True))
            if len(origins) != 1:
                raise ConfigurationException(
                    msg=f"包/模块来源必须唯一: {prefix}，发现 {len(origins)} 处: "
                    + ", ".join(str(path) for path in sorted(origins))
                )
            source = next(iter(origins))
            needs_package = index < len(parts) - 1 or package
            if needs_package and source.name != "__init__.py":
                raise ConfigurationException(msg=f"必须是含 __init__.py 的普通包: {prefix}")
            if parent is not None and not source.is_relative_to(parent):
                raise ConfigurationException(msg=f"包/模块来源越出父包: {prefix} -> {source}")
            if prefix in sys.modules:
                cls.validate_loaded(sys.modules[prefix], prefix, source)
            if needs_package:
                parent = source.parent
                search_paths = [str(parent)]
        return source

    @staticmethod
    def validate_loaded(module: ModuleType, name: str, expected: Path) -> None:
        """__file__、spec.origin 与包搜索路径必须指向本次确定的精确位置。"""
        if not isinstance(module, ModuleType):
            raise ConfigurationException(msg=f"模块缓存不是已加载模块: {name}")
        namespace = vars(module)
        spec = namespace.get("__spec__")
        origins = (namespace.get("__file__"), spec.origin if spec is not None else None)
        if any(
            not isinstance(origin, str) or Path(origin).resolve() != expected for origin in origins
        ):
            raise ConfigurationException(msg=f"模块来源不匹配: {name}，预期 {expected}")
        if expected.name == "__init__.py":
            paths = namespace.get("__path__")
            if paths is None or tuple(Path(path).resolve() for path in paths) != (expected.parent,):
                raise ConfigurationException(
                    msg=f"父包搜索路径不匹配: {name}，预期 {expected.parent}"
                )

    @classmethod
    def import_source(cls, name: str, expected: Path) -> ModuleType:
        """使用正常 import 身份与锁；不重新执行缓存模块或清空其他应用的缓存。"""
        if cls.locate(name) != expected:
            raise ConfigurationException(msg=f"导入来源不匹配: {name}，预期 {expected}")
        module = importlib.import_module(name)
        cls.validate_loaded(module, name, expected)
        # 父包初始化可能改变 __path__，返回定义前再次验证完整链。
        if cls.locate(name) != expected:
            raise ConfigurationException(msg=f"导入后来源发生变化: {name}，预期 {expected}")
        return module
