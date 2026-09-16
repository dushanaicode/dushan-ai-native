from dataclasses import dataclass, field

from sqlalchemy import Table, inspect
from sqlalchemy.orm import Mapper

from framework.starter_tenant.enums.tenant_model_kind import TenantModelKind


@dataclass(frozen=True, slots=True)
class TenantModel:
    target: type | Table
    kind: TenantModelKind
    tenant_column: str | None
    table: Table = field(init=False, repr=False)
    model: type | None = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.kind, TenantModelKind):
            raise TypeError("模型必须明确声明租户或全局归属")
        if isinstance(self.target, Table):
            table, model = self.target, None
        else:
            mapper = inspect(self.target, raiseerr=False)
            if not isinstance(mapper, Mapper) or len(mapper.tables) != 1:
                raise ValueError("租户模型只接受明确的单表映射")
            table, model = mapper.local_table, self.target
        object.__setattr__(self, "table", table)
        object.__setattr__(self, "model", model)
        if not table.primary_key.columns:
            raise ValueError("租户受管表必须声明主键")
        if self.kind is TenantModelKind.GLOBAL:
            if self.tenant_column is not None:
                raise ValueError("全局模型不能同时声明租户过滤列")
        elif self.tenant_column not in table.c:
            raise ValueError("租户模型必须声明租户列")
        elif (
            table.c[self.tenant_column].nullable
            or table.c[self.tenant_column].type.python_type is not str
        ):
            raise ValueError("租户列必须为非空字符串，与 Native 身份契约一致")

    @property
    def public(self):
        return self.kind is TenantModelKind.GLOBAL

    @property
    def authority_columns(self):
        return () if self.public else (self.tenant_column,)
