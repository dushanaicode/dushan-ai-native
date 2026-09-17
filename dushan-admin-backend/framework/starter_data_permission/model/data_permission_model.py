from dataclasses import dataclass, field

from sqlalchemy import Table, inspect
from sqlalchemy.orm import Mapper


@dataclass(frozen=True, slots=True)
class DataPermissionModel:
    """每张受管表明确公开或受保护；列必须来自同一张受控表。"""

    target: type | Table
    public: bool
    tenant_column: str | None
    membership_column: str | None = None
    department_column: str | None = None
    resource: str | None = None
    table: Table = field(init=False, repr=False)
    model: type | None = field(init=False, repr=False)

    def __post_init__(self):
        if type(self.public) is not bool:
            raise ValueError("公开声明必须使用布尔值")
        if isinstance(self.target, Table):
            table, model = self.target, None
        else:
            mapper = inspect(self.target, raiseerr=False)
            if not isinstance(mapper, Mapper) or len(mapper.tables) != 1:
                raise ValueError("数据权限只接受明确的单表映射")
            table, model = mapper.local_table, self.target
        object.__setattr__(self, "table", table)
        object.__setattr__(self, "model", model)
        resource = table.key if self.resource is None else self.resource
        if not isinstance(resource, str) or not resource.strip() or resource != resource.strip():
            raise ValueError("数据权限资源标识不能为空或包含首尾空白")
        object.__setattr__(self, "resource", resource)
        if any(column.key.startswith("_dushan_dp_") for column in table.columns):
            raise ValueError("列名不能使用数据权限绑定参数的保留前缀")
        if not table.primary_key.columns:
            raise ValueError("受管数据模型必须声明主键")
        if not self.public and (
            self.tenant_column is None or not (self.membership_column or self.department_column)
        ):
            raise ValueError("受保护模型必须声明租户及至少一类归属列")
        if self.public and (self.membership_column or self.department_column):
            raise ValueError("公开模型不能同时声明记录范围")
        if len(set(self.authority_columns)) != len(self.authority_columns):
            raise ValueError("租户与归属列不能复用")
        for name in self.authority_columns:
            allowed = (str,) if name == self.tenant_column else (int, str)
            if name not in table.c or table.c[name].type.python_type not in allowed:
                raise ValueError("租户列必须为字符串，用户/部门归属列必须为整数或字符串")

    def scope_values(self, column, values):
        """在已声明列的边界转换身份 ID，拒绝非规范或越界整数。"""
        if self.table.c[column].type.python_type is str:
            return values
        converted = set()
        for value in values:
            if not value.isascii() or not value.isdecimal():
                raise ValueError("整数归属列要求十进制身份 ID")
            identifier = int(value)
            if str(identifier) != value or not 0 < identifier <= 2**63 - 1:
                raise ValueError("整数归属 ID 必须是规范的正 int64")
            converted.add(identifier)
        return frozenset(converted)

    @property
    def authority_columns(self):
        return tuple(
            name
            for name in (self.tenant_column, self.membership_column, self.department_column)
            if name is not None
        )
