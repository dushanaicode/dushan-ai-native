from sqlalchemy.engine import IteratorResult
from sqlalchemy.engine.cursor import _NO_RESULT_METADATA


class WriteResult(IteratorResult):
    """保存受管分批 INSERT 的返回行和主键，不保留游标或连接。"""

    def __init__(
        self, metadata, rows, *, rowcount, primary_keys, generated_id=None, returns_rows=False
    ):
        super().__init__(
            metadata._for_freeze() if returns_rows else _NO_RESULT_METADATA, iter(rows)
        )
        self.returns_rows = returns_rows
        self.rowcount = rowcount
        self.inserted_primary_key_rows = primary_keys
        self.generated_id = generated_id

    @property
    def inserted_primary_key(self):
        if len(self.inserted_primary_key_rows) != 1:
            raise ValueError("多行 INSERT 请读取 inserted_primary_key_rows")
        return self.inserted_primary_key_rows[0]
