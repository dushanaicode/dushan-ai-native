class SqlTemplate:
    """保守词法扫描：仅输出固定结构词和符号，不信任 SQL 编译器的字面值标记。"""

    _KEYWORDS = frozenset(
        "SELECT INSERT UPDATE DELETE MERGE INTO VALUES FROM WHERE SET JOIN LEFT RIGHT "
        "INNER OUTER FULL CROSS ON AS AND OR NOT IN IS LIKE BETWEEN EXISTS DISTINCT "
        "ORDER BY GROUP HAVING LIMIT OFFSET FETCH FIRST NEXT ROWS ROW ONLY RETURNING "
        "UNION ALL INTERSECT EXCEPT WITH RECURSIVE CASE WHEN THEN ELSE END ASC DESC "
        "CREATE ALTER DROP TABLE INDEX VIEW IF CONFLICT DO NOTHING DUPLICATE KEY "
        "USING MATCHED OVER PARTITION FOR SHARE LOCK NOWAIT SKIP LOCKED EXPLAIN "
        "ANALYZE TRUNCATE SAVEPOINT RELEASE ROLLBACK TO PRAGMA SHOW DESCRIBE "
        "CAST COLLATE NULLS LAST DEFAULT CONSTRAINT PRIMARY FOREIGN REFERENCES "
        "CHECK UNIQUE ADD COLUMN MATERIALIZED REPLACE IGNORE TOP OUTFILE".split()
    )
    _OPERATIONS = frozenset(
        "SELECT INSERT UPDATE DELETE MERGE CREATE ALTER DROP TRUNCATE WITH "
        "EXPLAIN ANALYZE SAVEPOINT RELEASE ROLLBACK PRAGMA SHOW DESCRIBE".split()
    )

    @classmethod
    def render(cls, statement: str, *, max_length: int) -> tuple[str, str | None]:
        # 超长 SQL 不截取原文后解析；截断可能把秘密尾部误作新的结构。
        if len(statement) > max_length:
            return "UNKNOWN", None
        tokens = []
        index, length = 0, len(statement)
        while index < length:
            char = statement[index]
            if char.isspace():
                index += 1
                continue
            if statement.startswith("--", index) or char == "#":
                newline = statement.find("\n", index)
                index = length if newline < 0 else newline + 1
                continue
            if statement.startswith("/*", index):
                index += 2
                depth = 1
                while index < length and depth:
                    if statement.startswith("/*", index):
                        depth += 1
                        index += 2
                    elif statement.startswith("*/", index):
                        depth -= 1
                        index += 2
                    else:
                        index += 1
                continue
            if char in "'\"`[":
                end = "]" if char == "[" else char
                index += 1
                while index < length:
                    if statement[index] == "\\":
                        index += 2
                    elif statement[index] == end:
                        index += 1
                        if index < length and statement[index] == end:
                            index += 1
                        else:
                            break
                    else:
                        index += 1
                tokens.append("?")
                continue
            if char == "$":
                delimiter_end = index + 1
                while delimiter_end < length and (
                    statement[delimiter_end].isalnum() or statement[delimiter_end] == "_"
                ):
                    delimiter_end += 1
                if delimiter_end < length and statement[delimiter_end] == "$":
                    delimiter = statement[index : delimiter_end + 1]
                    closing = statement.find(delimiter, delimiter_end + 1)
                    index = length if closing < 0 else closing + len(delimiter)
                else:
                    index = delimiter_end
                tokens.append("?")
                continue
            if statement.startswith("%(", index):
                closing = statement.find(")", index + 2)
                index = length if closing < 0 else min(length, closing + 2)
                tokens.append("?")
                continue
            if char in ":@?":
                if statement.startswith("::", index):
                    tokens.append("::")
                    index += 2
                    continue
                index += 1
                while index < length and (statement[index].isalnum() or statement[index] in "_$"):
                    index += 1
                tokens.append("?")
                continue
            if char.isalnum() or char == "_":
                start = index
                index += 1
                while index < length and (statement[index].isalnum() or statement[index] in "_$"):
                    index += 1
                word = statement[start:index].upper()
                # 标识符也可能来自 literal_column，绝不把未知名称送入事件。
                tokens.append(word if word in cls._KEYWORDS else "?")
                continue
            tokens.append(char if char in "+-*/%=<>!|&^~(),.;" else "?")
            index += 1
        operation = tokens[0] if tokens and tokens[0] in cls._OPERATIONS else "UNKNOWN"
        return operation, " ".join(tokens)
