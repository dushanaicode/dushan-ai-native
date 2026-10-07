import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pymysql
from pymysql.constants import CLIENT

REPO = Path(__file__).resolve().parents[3]
DEV_STATE = REPO / "dushan-admin-backend/Temp/native-dev/state.json"
DEV_RESOURCES = REPO / "dushan-admin-backend/Temp/native-dev/development-resources.json"
TEST_RESOURCES = REPO / "Temp/test-resources/resources.json"
SQL_ROOT = REPO / "dushan-admin-backend/sql/mysql"
REPORT_DIR = REPO / "Temp/test-resources/reports"
DEV_DATABASE = "dushan_native_dev"
AUDIT_COLUMNS = {"create_time", "update_time", "creator", "updater"}


def connect(port, password, database=None):
    return pymysql.connect(
        host="127.0.0.1",
        port=port,
        user="root",
        password=password,
        database=database,
        autocommit=True,
        charset="utf8mb4",
        client_flag=CLIENT.MULTI_STATEMENTS,
    )


def build_reference(connection, name):
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{name}`")
        for folder in ("system", "infra"):
            for sql in sorted((SQL_ROOT / folder).glob("*.sql")):
                cursor.execute(sql.read_text(encoding="utf-8"))
                while cursor.nextset():
                    pass


def schema(connection, database):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'",
            (database,),
        )
        tables = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, ORDINAL_POSITION"
            " FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s",
            (database,),
        )
        columns = {(row[0], row[1]): row[2:6] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT TABLE_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION)"
            " FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s GROUP BY TABLE_NAME",
            (database,),
        )
        orders = dict(cursor.fetchall())
        cursor.execute(
            "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX)"
            " FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE",
            (database,),
        )
        indexes = {(row[0], row[1]): row[2:] for row in cursor.fetchall()}
    return tables, columns, indexes, orders


def rows_by_id(connection, database, table):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM `{database}`.`{table}`")
        names = [item[0] for item in cursor.description]
        key = names.index("id")
        return names, {row[key]: row for row in cursor.fetchall()}


def compare_schema(dev, reference, reference_name):
    dev_tables, dev_columns, dev_indexes, dev_orders = schema(dev, DEV_DATABASE)
    ref_tables, ref_columns, ref_indexes, ref_orders = schema(reference, reference_name)
    order_only = sorted(
        t
        for t in dev_tables & ref_tables
        if dev_orders[t] != ref_orders[t]
        and set(dev_orders[t].split(",")) == set(ref_orders[t].split(","))
    )
    return order_only, {
        "缺少的表": sorted(ref_tables - dev_tables),
        "多出的表": sorted(dev_tables - ref_tables),
        "缺少的列": sorted(
            f"{t}.{c}" for t, c in ref_columns.keys() - dev_columns.keys() if t in dev_tables
        ),
        "多出的列": sorted(
            f"{t}.{c}" for t, c in dev_columns.keys() - ref_columns.keys() if t in ref_tables
        ),
        "定义不同的列": sorted(
            f"{t}.{c}: 开发库={dev_columns[(t, c)]} 仓库={ref_columns[(t, c)]}"
            for t, c in dev_columns.keys() & ref_columns.keys()
            if dev_columns[(t, c)] != ref_columns[(t, c)]
        ),
        "缺少的索引": sorted(
            f"{t}.{i}" for t, i in ref_indexes.keys() - dev_indexes.keys() if t in dev_tables
        ),
        "多出的索引": sorted(
            f"{t}.{i}" for t, i in dev_indexes.keys() - ref_indexes.keys() if t in ref_tables
        ),
        "定义不同的索引": sorted(
            f"{t}.{i}"
            for t, i in dev_indexes.keys() & ref_indexes.keys()
            if dev_indexes[(t, i)] != ref_indexes[(t, i)]
        ),
    }


def compare_seeds(dev, reference, reference_name):
    result = {}
    with reference.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND COLUMN_NAME='id'",
            (reference_name,),
        )
        tables = sorted(row[0] for row in cursor.fetchall())
    for table in tables:
        names, ref_rows = rows_by_id(reference, reference_name, table)
        if not ref_rows:
            continue
        dev_names, dev_rows = rows_by_id(dev, DEV_DATABASE, table)
        if dev_names != names:
            result[table] = {"说明": "列结构不同，先处理表结构差异"}
            continue
        compared = [i for i, name in enumerate(names) if name not in AUDIT_COLUMNS]
        changed = [
            k
            for k in ref_rows.keys() & dev_rows.keys()
            if [ref_rows[k][i] for i in compared] != [dev_rows[k][i] for i in compared]
        ]
        missing = sorted(ref_rows.keys() - dev_rows.keys())
        if changed or missing:
            result[table] = {
                "种子行": len(ref_rows),
                "开发库缺少的种子行": [str(k) for k in missing],
                "内容不同的行": len(changed),
                "不同的列": sorted(
                    {
                        names[i]
                        for k in changed
                        for i in compared
                        if ref_rows[k][i] != dev_rows[k][i]
                    }
                ),
            }
    return result


def main():
    dev_port = json.loads(DEV_RESOURCES.read_text(encoding="utf-8"))["mysql_port"]
    dev_password = json.loads(DEV_STATE.read_text(encoding="utf-8"))["root_password"]
    test_port = json.loads(TEST_RESOURCES.read_text(encoding="utf-8"))["mysql_port"]
    dev = connect(dev_port, dev_password)
    reference = connect(test_port, "")
    reference_name = "drift_reference_" + uuid4().hex[:12]
    build_reference(reference, reference_name)
    try:
        order_only, structure = compare_schema(dev, reference, reference_name)
        report = {
            "时间": datetime.now().isoformat(timespec="seconds"),
            "表结构": structure,
            "仅列顺序不同的表": order_only,
            "种子数据": compare_seeds(dev, reference, reference_name),
        }
    finally:
        with reference.cursor() as cursor:
            cursor.execute(f"DROP DATABASE `{reference_name}`")
        dev.close()
        reference.close()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORT_DIR / "dev-db-drift.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    schema_items = sum(len(items) for items in report["表结构"].values())
    print(f"表结构差异：{schema_items} 项（不为 0 时开发库需要升级）")
    for name, items in report["表结构"].items():
        for item in items:
            print(f"  {name}：{item}")
    print(f"仅列顺序不同的表：{report['仅列顺序不同的表']}（不影响使用，不计入升级判断）")
    print(
        f"种子数据不同的表：{len(report['种子数据'])} 个（其中可能包含正常的运行数据变化，需要人工判断）"
    )
    for table, detail in report["种子数据"].items():
        print(f"  {table}：{detail}")
    print(f"完整报告：{output}")
    return 1 if schema_items else 0


if __name__ == "__main__":
    sys.exit(main())
