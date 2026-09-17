import argparse
import importlib
import sys
from pathlib import Path

from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.ddl.ddl_exporter import DdlExporter
from framework.starter_database.model.base import Base


class DdlCli:
    """导出业务模块建表脚本的命令行入口。

    模型只有被导入后才会注册到元数据，因此先按包路径递归导入全部 DO 再编译。
    """

    @staticmethod
    def parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="ddl-export", description="从模型导出建表 SQL")
        parser.add_argument("--package", required=True, help="业务模块包名，例如 module_system")
        parser.add_argument(
            "--dialect", required=True, choices=DdlDialects.names(), help="目标数据库方言"
        )
        parser.add_argument("--output", type=Path, help="输出文件；省略时打印到标准输出")
        parser.add_argument("--title", default="", help="写入文件头的脚本说明")
        return parser

    @classmethod
    def main(cls) -> int:
        arguments = cls.parser().parse_args()
        count = cls._import_models(arguments.package)
        if not count:
            raise ValueError(f"{arguments.package} 下没有找到任何模型文件")
        exporter = DdlExporter(Base.metadata, arguments.dialect)
        script = exporter.export(title=arguments.title or f"{arguments.package} 建表脚本")
        if arguments.output is None:
            sys.stdout.write(script)
            return 0
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(script, encoding="utf-8", newline="\n")
        sys.stdout.write(
            f"已导出 {len(Base.metadata.tables)} 张表到 {arguments.output}（{arguments.dialect}）\n"
        )
        return 0

    @staticmethod
    def _import_models(package: str) -> int:
        """递归导入包内全部 *_do.py，返回导入的模型文件数。"""
        module = importlib.import_module(package)
        root = Path(module.__file__).parent
        names = [
            ".".join((package, *path.relative_to(root).with_suffix("").parts))
            for path in sorted(root.rglob("*_do.py"))
        ]
        for name in names:
            importlib.import_module(name)
        return len(names)
