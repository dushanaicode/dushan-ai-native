from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pymysql
import pytest


@pytest.fixture(params=["name", "type", "value"])
def dictionary_key(request):
    """分别构造名称、类型以及同类型键值冲突，避免其他唯一键干扰。"""
    key = "unique_" + uuid4().hex
    if request.param == "value":
        return "system_dict_data", {"dict_type": key, "value": key}, {"label": key}
    other = "type" if request.param == "name" else "name"
    return "system_dict_type", {request.param: key}, {other: key}


def insert_dictionary_row(connection, table, values):
    """直接插入字典记录，验证数据库自身能拒绝绕过服务预检的重复写入。"""
    values = {**values, "creator": "", "updater": ""}
    if table == "system_dict_data":
        values["sort"] = 0
    columns = ", ".join(f"`{column}`" for column in values)
    placeholders = ", ".join("%s" for _ in values)
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO `{table}` ({columns}, status, deleted, create_time, update_time) "
            f"VALUES ({placeholders}, 1, 0, UTC_TIMESTAMP(), UTC_TIMESTAMP())",
            tuple(values.values()),
        )
        return cursor.lastrowid


def test_database_rejects_duplicates_and_reuses_deleted_dictionary_keys(
    system_database, dictionary_key
):
    """直接重复写入失败，连续软删三次后仍能复用同一业务键。"""
    _, _, connection = system_database
    table, unique, other = dictionary_key
    deleted_ids = []
    for index in range(3):
        identifier = insert_dictionary_row(
            connection,
            table,
            {**unique, **{column: value + str(index) for column, value in other.items()}},
        )
        with pytest.raises(pymysql.IntegrityError) as captured:
            insert_dictionary_row(connection, table, {**unique, **other})
        assert captured.value.args[0] == 1062
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE `{table}` SET deleted = 1 WHERE id = %s", (identifier,))
            cursor.execute(f"SELECT active_key FROM `{table}` WHERE id = %s", (identifier,))
            assert cursor.fetchone() == (None,)
        deleted_ids.append(identifier)
    identifier = insert_dictionary_row(connection, table, {**unique, **other})
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT active_key FROM `{table}` WHERE id = %s", (identifier,))
        assert cursor.fetchone() == (1,)
    assert len(set(deleted_ids + [identifier])) == 4


def test_concurrent_dictionary_creates_have_one_winner(system_database, dictionary_key):
    """两个事务均预检为空后并发写入，同一业务键只能有一个事务提交。"""
    resources, database, _ = system_database
    table, unique, other = dictionary_key
    ready = Barrier(2)

    def create(index):
        """用独立事务模拟先查后写的竞争，并记录数据库唯一约束结果。"""
        connection = pymysql.connect(
            host="127.0.0.1",
            port=resources["mysql_port"],
            user="root",
            password="",
            database=database,
            charset="utf8mb4",
            autocommit=False,
        )
        try:
            conditions = " AND ".join(f"`{column}` = %s" for column in unique)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id FROM `{table}` WHERE {conditions} AND deleted = 0",
                    tuple(unique.values()),
                )
                assert cursor.fetchall() == ()
            ready.wait(timeout=10)
            try:
                insert_dictionary_row(
                    connection,
                    table,
                    {**unique, **{column: value + str(index) for column, value in other.items()}},
                )
                connection.commit()
                return 0
            except pymysql.IntegrityError as error:
                connection.rollback()
                return error.args[0]
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert sorted(results) == [0, 1062]
