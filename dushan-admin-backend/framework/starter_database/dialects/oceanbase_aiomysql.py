from sqlalchemy.dialects.mysql.aiomysql import MySQLDialect_aiomysql


class OceanBaseAiomysqlDialect(MySQLDialect_aiomysql):
    """OceanBase MySQL 模式显式初始化事务状态，不依赖握手自动提交标记。"""

    # SQL 语法及 Table/Constraint 选项仍使用 MySQL 方言族。
    supports_statement_cache = True

    def on_connect(self):
        parent = super().on_connect()

        def configure(connection):
            if parent is not None:
                parent(connection)
            cursor = connection.cursor()
            try:
                cursor.execute("SET SESSION autocommit=0")
            finally:
                cursor.close()

        return configure
