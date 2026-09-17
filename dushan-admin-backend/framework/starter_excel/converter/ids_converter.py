import csv
import io
from dataclasses import dataclass
from typing import Literal

from framework.common.contracts.snowflake_id import SnowflakeId
from framework.starter_excel.model.conversion_context import ConversionContext
from framework.starter_excel.spi.name_provider import NameProvider


@dataclass(frozen=True)
class IdsConverter:
    """部门或岗位 ID 集合双向转换；CSV 引号保留名称中的逗号及双引号。"""

    kind: Literal["departments", "posts"]

    def _provider(self, context: ConversionContext) -> NameProvider:
        provider = getattr(context.providers, self.kind)
        if provider is None:
            raise ValueError(f"未提供 {self.kind} Provider")
        return provider

    async def to_excel(self, value: list[int] | set[int], context: ConversionContext) -> str:
        normalized = [int(SnowflakeId.format(item)) for item in value]
        ids = sorted(set(normalized)) if isinstance(value, set) else list(dict.fromkeys(normalized))
        names = context.lookups.setdefault((self.kind, "names"), {})
        missing = [value for value in ids if value not in names]
        if missing:
            fetched = await self._provider(context).names(missing)
            if any(value not in fetched or not fetched[value] for value in missing):
                raise ValueError("引用的部门或岗位不存在")
            names.update(fetched)
        output = io.StringIO(newline="")
        csv.writer(output, lineterminator="").writerow(names[value] for value in ids)
        return output.getvalue()

    async def to_python(self, value: str, context: ConversionContext) -> list[int]:
        rows = list(csv.reader(io.StringIO(value, newline=""), strict=True))
        if len(rows) != 1:
            raise ValueError("部门或岗位名称必须是一行 CSV")
        names = list(dict.fromkeys(rows[0]))
        ids = context.lookups.setdefault((self.kind, "ids"), {})
        missing = [value for value in names if value not in ids]
        if missing:
            fetched = await self._provider(context).ids(missing)
            if any(value not in fetched for value in missing):
                raise ValueError("引用的部门或岗位名称不存在")
            ids.update(fetched)
        return [ids[value] for value in names]
