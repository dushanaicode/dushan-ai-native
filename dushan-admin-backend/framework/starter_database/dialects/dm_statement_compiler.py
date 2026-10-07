from dmSQLAlchemy.dmpython import DMCompiler_dmPython
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import AsBoolean, False_, True_


class DmStatementCompiler(DMCompiler_dmPython):
    """按 DM 的数值布尔类型编译 IS 判断，保留 NULL 的二值判断语义。"""

    def visit_binary(self, binary, **kwargs):
        if binary.operator in (operators.is_, operators.is_not) and isinstance(
            binary.right, (True_, False_)
        ):
            left = self.process(binary.left, **kwargs)
            if binary.left._is_implicitly_boolean or isinstance(binary.left, AsBoolean):
                condition = left if isinstance(binary.right, True_) else f"NOT ({left})"
            else:
                condition = f"{left} = {self.process(binary.right, **kwargs)}"
            expected = 1 if binary.operator is operators.is_ else 0
            return f"(CASE WHEN {condition} THEN 1 ELSE 0 END = {expected})"
        return super().visit_binary(binary, **kwargs)
