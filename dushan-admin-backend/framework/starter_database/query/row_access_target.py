from dataclasses import dataclass

from sqlalchemy import Table


@dataclass(frozen=True, slots=True)
class RowAccessTarget:
    table: Table
    model: type | None
    public: bool
    tenant_column: str | None
    authority_columns: tuple[str, ...]
