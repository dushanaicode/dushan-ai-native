import argparse
import re
from pathlib import Path

from sqlalchemy import Boolean

from framework.starter_database.ddl.ddl_cli import DdlCli
from framework.starter_database.ddl.ddl_dialects import DdlDialects
from framework.starter_database.model.base import Base


class SeedSqlConverter:
    """把 MySQL 空库种子转换为模型对应的方言，不接受未声明的 SQL 语法。"""

    _TOKEN = re.compile(
        r"\s+|--[^\n]*|/\*.*?\*/|[bB]'[01]+'|'(?:''|\\.|[^'\\])*'"
        r"|`(?:``|[^`])*`|[A-Za-z_][A-Za-z_0-9]*|[+-]?\d+(?:\.\d+)?|[(),;=]",
        re.DOTALL,
    )
    _ESCAPES = {
        "0": "\0",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "%": "\\%",
        "_": "\\_",
    }

    @staticmethod
    def tokens(source: str) -> list[str]:
        """按 MySQL 字符串规则分词，字符串内的逗号和分号不参与语句分割。"""
        tokens = []
        end = 0
        for match in SeedSqlConverter._TOKEN.finditer(source):
            if match.start() != end:
                raise ValueError(f"不支持的种子 SQL：{source[end : match.start()]!r}")
            token = match.group()
            end = match.end()
            if not token.isspace() and not token.startswith(("--", "/*")):
                tokens.append(token)
        if end != len(source):
            raise ValueError(f"种子 SQL 未完整解析：{source[end:]!r}")
        return tokens

    @staticmethod
    def _string(token: str) -> str:
        """解码 MySQL 的反斜杠和双单引号转义。"""
        return re.sub(
            r"\\(.)|''",
            SeedSqlConverter._unescape,
            token[1:-1],
            flags=re.DOTALL,
        )

    @staticmethod
    def _unescape(match: re.Match) -> str:
        """转换一个 MySQL 转义；未定义的转义按 MySQL 规则去掉反斜杠。"""
        if match.group() == "''":
            return "'"
        return SeedSqlConverter._ESCAPES.get(match[1], match[1])

    @staticmethod
    def _value(tokens: list[str], column, dialect_name: str) -> str:
        """依照真实列类型转换字面量及 UTC 时间表达式。"""
        expression = "".join(tokens)
        if expression.upper() in ("NOW()", "UTC_TIMESTAMP()"):
            if dialect_name == "dm":
                return "GETUTCDATE()"
            return "(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')"
        if len(tokens) != 1:
            raise ValueError(f"不支持的种子表达式：{expression}")
        if expression.upper() == "NULL":
            return "NULL"
        if expression.startswith("'"):
            value = SeedSqlConverter._string(expression)
            if "\0" in value:
                raise ValueError("种子字符串不能包含 NUL")
            return "'" + value.replace("'", "''") + "'"
        if expression.lower().startswith("b'"):
            expression = str(int(expression[2:-1], 2))
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", expression):
            raise ValueError(f"不支持的种子表达式：{expression}")
        if isinstance(column.type, Boolean):
            if expression not in ("0", "1"):
                raise ValueError(f"布尔列 {column} 只接受 0 或 1")
            if dialect_name != "dm":
                return "TRUE" if expression == "1" else "FALSE"
        return expression

    @staticmethod
    def _insert(tokens: list[str], dialect_name: str) -> tuple[str, list[str]]:
        """解析当前种子的 INSERT VALUES，并按方言输出一条或多条 INSERT。"""
        index = 1
        if tokens[index].upper() == "IGNORE":
            index += 1
        if tokens[index].upper() != "INTO" or tokens[index + 2] != "(":
            raise ValueError("种子只支持带显式列名的 INSERT INTO")
        table = Base.metadata.tables[tokens[index + 1].strip("`")]
        index += 3
        columns = []
        while tokens[index] != ")":
            columns.append(table.c[tokens[index].strip("`")])
            index += 1
            if tokens[index] == ",":
                index += 1
            elif tokens[index] != ")":
                raise ValueError("种子列名之间必须使用逗号")
        if tokens[index + 1].upper() != "VALUES":
            raise ValueError("种子只支持 INSERT VALUES")
        index += 2
        rows = []
        while index < len(tokens):
            if tokens[index] != "(":
                raise ValueError("种子 VALUES 必须由括号包围")
            index += 1
            row = []
            for column in columns:
                start = index
                depth = 0
                while index < len(tokens):
                    token = tokens[index]
                    if depth == 0 and token in (",", ")"):
                        break
                    depth += (token == "(") - (token == ")")
                    index += 1
                row.append(SeedSqlConverter._value(tokens[start:index], column, dialect_name))
                expected = ")" if len(row) == len(columns) else ","
                if tokens[index] != expected:
                    raise ValueError(f"{table.name} 的种子列数与值数不一致")
                index += 1
            rows.append("(" + ", ".join(row) + ")")
            if index < len(tokens):
                if tokens[index] != ",":
                    raise ValueError("种子 VALUES 行之间必须使用逗号")
                index += 1
        preparer = DdlDialects.resolve(dialect_name).identifier_preparer
        names = ", ".join(preparer.quote(column.name) for column in columns)
        prefix = f"INSERT INTO {preparer.quote(table.name)} ({names}) VALUES"
        if dialect_name == "dm":
            statements = [f"{prefix}\n{row};" for row in rows]
            if any(column.identity is not None for column in columns):
                statements.insert(0, f"SET IDENTITY_INSERT {preparer.quote(table.name)} ON;")
                statements.append(f"SET IDENTITY_INSERT {preparer.quote(table.name)} OFF;")
            return table.name, statements
        return table.name, [prefix + "\n" + ",\n".join(rows) + ";"]

    @staticmethod
    def convert(source: str, dialect_name: str, source_name: str) -> str:
        """转换一个种子文件；输出只用于空库首次装载，所有数据错误直接暴露。"""
        if dialect_name not in ("postgresql", "dm"):
            raise ValueError(f"不支持的种子转换方言：{dialect_name}")
        blocks = [
            f"-- 由 {source_name} 生成；请修改 MySQL 源文件后重新生成。",
            "-- 仅用于空库首次初始化，不支持重复执行。",
        ]
        if dialect_name == "postgresql":
            blocks.append("SET standard_conforming_strings = on;")
        statement = []
        seeded_tables = set()
        for token in SeedSqlConverter.tokens(source):
            if token != ";":
                statement.append(token)
                continue
            if statement[0].upper() == "SET":
                if [item.upper() for item in statement] not in (
                    ["SET", "NAMES", "UTF8MB4"],
                    ["SET", "TIME_ZONE", "=", "'+00:00'"],
                ):
                    raise ValueError(f"不支持的会话设置：{statement}")
            elif statement[0].upper() == "INSERT":
                table_name, inserts = SeedSqlConverter._insert(statement, dialect_name)
                seeded_tables.add(table_name)
                blocks.extend(inserts)
            else:
                raise ValueError(f"不支持的种子语句：{statement[0]}")
            statement = []
        if statement:
            raise ValueError("种子语句缺少结尾分号")
        if dialect_name == "postgresql":
            preparer = DdlDialects.resolve(dialect_name).identifier_preparer
            for name in sorted(seeded_tables):
                for column in Base.metadata.tables[name].columns:
                    if column.identity is not None:
                        table_sql = preparer.quote(name)
                        column_sql = preparer.quote(column.name)
                        blocks.append(
                            f"SELECT setval(pg_get_serial_sequence('{table_sql}', '{column.name}'), "
                            f"MAX({column_sql}), true) FROM {table_sql};"
                        )
        return "\n\n".join(blocks) + "\n"

    @staticmethod
    def generate(sql_root: Path, output_root: Path) -> list[Path]:
        """从 MySQL 种子生成其他六种数据库各自的文件，返回全部输出路径。"""
        for module in ("system", "infra"):
            DdlCli._import_models(f"module_{module}")
        outputs = []
        for module in ("system", "infra"):
            for source in sorted((sql_root / "mysql" / module).glob("0[1-3]_*.sql")):
                original = source.read_bytes()
                source_name = source.relative_to(sql_root).as_posix()
                for dialect_name, targets in (
                    ("mysql", ("tidb", "oceanbase")),
                    ("postgresql", ("postgresql", "opengauss", "kingbase")),
                    ("dm", ("dm",)),
                ):
                    result = original
                    if dialect_name != "mysql":
                        result = SeedSqlConverter.convert(
                            original.decode("utf-8"), dialect_name, source_name
                        ).encode("utf-8")
                    for dialect in targets:
                        target = output_root / dialect / module / source.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(result)
                        outputs.append(target)
        return outputs

    @staticmethod
    def main() -> int:
        """接收 SQL 来源和输出根目录并执行确定性生成。"""
        parser = argparse.ArgumentParser(description="从 MySQL 空库种子生成其他方言")
        parser.add_argument("--sql-root", type=Path, required=True)
        parser.add_argument("--output-root", type=Path, required=True)
        arguments = parser.parse_args()
        outputs = SeedSqlConverter.generate(arguments.sql_root, arguments.output_root)
        print(f"已生成 {len(outputs)} 份种子 SQL")
        return 0


if __name__ == "__main__":
    raise SystemExit(SeedSqlConverter.main())
