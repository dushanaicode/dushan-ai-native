import sqlalchemy
from sqlalchemy import (
    BINARY,
    CHAR,
    JSON,
    NCHAR,
    NVARCHAR,
    TIMESTAMP,
    VARBINARY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Float,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    Unicode,
    UnicodeText,
)
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.types import TypeEngine

_TYPES = {
    "bigint": BigInteger,
    "int": Integer,
    "smallint": SmallInteger,
    "float": Float,
    "double": Double,
    "decimal": Numeric,
    "boolean": Boolean,
    "varchar": String,
    "char": CHAR,
    "unicode": Unicode,
    "nvarchar": NVARCHAR,
    "nchar": NCHAR,
    "text": Text,
    "ntext": UnicodeText,
    "json": JSON,
    "date": Date,
    "datetime": DateTime,
    "timestamp": TIMESTAMP,
    "time": Time,
    "blob": LargeBinary,
    "binary": BINARY,
    "varbinary": VARBINARY,
}
_MYSQL_VARIANTS = {
    "tinyint": (SmallInteger, mysql.TINYINT()),
    "mediumint": (Integer, mysql.MEDIUMINT()),
    "tinytext": (Text, mysql.TINYTEXT()),
    "mediumtext": (Text, mysql.MEDIUMTEXT()),
    "longtext": (Text, mysql.LONGTEXT()),
    "tinyblob": (LargeBinary, mysql.TINYBLOB()),
    "mediumblob": (LargeBinary, mysql.MEDIUMBLOB()),
    "longblob": (LargeBinary, mysql.LONGBLOB()),
    "bit": (Boolean, mysql.BIT(1)),
}
_TYPE_NAMES = {type_class: name for name, type_class in _TYPES.items()}
_TYPE_NAMES.update({type(variant): name for name, (_, variant) in _MYSQL_VARIANTS.items()})
_TYPE_NAMES.update(
    {
        type_class: name
        for name, classes in {
            "bigint": (sqlalchemy.BIGINT, mysql.BIGINT),
            "int": (sqlalchemy.INTEGER, mysql.INTEGER),
            "smallint": (sqlalchemy.SMALLINT, mysql.SMALLINT),
            "float": (sqlalchemy.FLOAT, mysql.FLOAT),
            "double": (sqlalchemy.DOUBLE, postgresql.DOUBLE_PRECISION, mysql.DOUBLE),
            "decimal": (sqlalchemy.NUMERIC, sqlalchemy.DECIMAL, mysql.NUMERIC, mysql.DECIMAL),
            "boolean": (sqlalchemy.BOOLEAN,),
            "varchar": (sqlalchemy.VARCHAR, mysql.VARCHAR),
            "char": (mysql.CHAR,),
            "nchar": (mysql.NCHAR,),
            "nvarchar": (mysql.NVARCHAR,),
            "text": (sqlalchemy.TEXT, mysql.TEXT),
            "json": (mysql.JSON, postgresql.JSON),
            "date": (sqlalchemy.DATE,),
            "datetime": (sqlalchemy.DATETIME, mysql.DATETIME),
            "timestamp": (mysql.TIMESTAMP, postgresql.TIMESTAMP),
            "time": (sqlalchemy.TIME, mysql.TIME, postgresql.TIME),
            "blob": (sqlalchemy.BLOB,),
        }.items()
        for type_class in classes
    }
)


class CodegenTypeUtils:
    """在反射、模型和建表 SQL 之间共享字段物理类型。"""

    @staticmethod
    def metadata(sql_type: TypeEngine) -> dict:
        """提取生成所需的类型参数；排序规则与字符集按项目建表约定处理，改变取值语义的选项明确拒绝。"""
        if (
            any(
                getattr(sql_type, option, False)
                for option in ("unsigned", "zerofill", "timezone", "fsp")
            )
            or (isinstance(sql_type, Float) and getattr(sql_type, "scale", None) is not None)
            or (
                isinstance(sql_type, (DateTime, Time))
                and getattr(sql_type, "precision", None) is not None
            )
            or (
                getattr(sql_type, "national", False) and not isinstance(sql_type, (NCHAR, NVARCHAR))
            )
        ):
            raise ValueError(f"代码生成暂不支持类型选项：{sql_type!r}")
        if type(sql_type) not in _TYPE_NAMES:
            raise ValueError(f"代码生成不支持数据库类型：{sql_type!r}")
        if isinstance(sql_type, mysql.BIT) and sql_type.length != 1:
            raise ValueError("代码生成仅支持 BIT(1)")
        data_type = _TYPE_NAMES[type(sql_type)]
        return {
            "data_type": data_type,
            "column_size": getattr(sql_type, "length", None),
            "numeric_precision": getattr(sql_type, "precision", None),
            "numeric_scale": getattr(sql_type, "scale", None),
            "type_metadata_synced": True,
        }

    @staticmethod
    def field_type(data_type: str) -> str:
        """按受支持的物理类型推导 Python 字段类型。"""
        type_class, _ = CodegenTypeUtils._type_classes(data_type)
        return "json" if type_class is JSON else type_class().python_type.__name__

    @staticmethod
    def _type_classes(data_type: str) -> tuple[type[TypeEngine], TypeEngine | None]:
        """解析已保存的物理类型，未知类型不降级为字符串。"""
        name = data_type.lower().strip()
        if name in _MYSQL_VARIANTS:
            return _MYSQL_VARIANTS[name]
        if name not in _TYPES:
            raise ValueError(f"代码生成不支持数据库类型：{data_type}")
        return _TYPES[name], None

    @staticmethod
    def sqlalchemy_type(column) -> TypeEngine:
        """从列元数据重建类型，字符串长度和数值精度不添加默认值。"""
        type_class, variant = CodegenTypeUtils._type_classes(column.data_type)
        if issubclass(type_class, (String, LargeBinary, BINARY, VARBINARY)):
            result = type_class(length=column.column_size)
        elif issubclass(type_class, Float):
            result = type_class(precision=column.numeric_precision)
        elif issubclass(type_class, Numeric):
            result = type_class(precision=column.numeric_precision, scale=column.numeric_scale)
        else:
            result = type_class()
        return result.with_variant(variant, "mysql") if variant else result

    @staticmethod
    def python_expression(column) -> str:
        """生成与建表 SQL 共用类型对象的 Python 表达式。"""
        sql_type = CodegenTypeUtils.sqlalchemy_type(column)
        _, variant = CodegenTypeUtils._type_classes(column.data_type)
        expression = repr(sql_type)
        if variant:
            expression += f'.with_variant(mysql.{variant!r}, "mysql")'
        return expression

    @staticmethod
    def sql_expression(column) -> str:
        """按附带建表脚本的 MySQL 方言编译同一物理类型。"""
        return str(CodegenTypeUtils.sqlalchemy_type(column).compile(dialect=mysql.dialect()))
