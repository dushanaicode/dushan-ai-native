from sqlalchemy import text

from framework.starter_database.connection.engine_entry import EngineEntry


class ReplicationStatus:
    """按具体方言读取复制状态；不支持或权限不足会明确报告。"""

    @staticmethod
    async def read(entry: EngineEntry) -> dict:
        async with entry.engine.connect() as connection:
            match entry.engine.dialect.name:
                case "mysql":
                    rows = (await connection.execute(text("SHOW REPLICA STATUS"))).mappings().all()
                    if len(rows) != 1:
                        raise ValueError("MySQL 副本检查要求一个已配置的复制通道")
                    row = rows[0]
                    lag = row["Seconds_Behind_Source"]
                    return {
                        "lag_seconds": lag,
                        "running": row["Replica_IO_Running"] == "Yes"
                        and row["Replica_SQL_Running"] == "Yes"
                        and lag is not None,
                    }
                case "postgresql":
                    row = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT pg_is_in_recovery() AS recovering, CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0 ELSE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - pg_last_xact_replay_timestamp())) END AS lag"
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    lag = row["lag"]
                    return {
                        "lag_seconds": None if lag is None else max(0.0, float(lag)),
                        "running": row["recovering"] and lag is not None,
                    }
                case _:
                    raise ValueError(f"复制状态尚未适配方言：{entry.engine.dialect.name}")
